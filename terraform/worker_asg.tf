# ==============================================================================
# ASG 2: Workers de Execução em Sandbox (Camada de Processamento / ASG 2)
# Contribuição de Felipe (feat/sqs-worker-async) integrada à infraestrutura VPC
# ==============================================================================

# Launch Template do Worker (AMI e configurações de boot em Sandbox)
resource "aws_launch_template" "worker_lt" {
  name_prefix   = "${var.project_name}-worker-lt-"
  image_id      = var.worker_ami != "" ? var.worker_ami : var.ec2_ami
  instance_type = var.ec2_instance_type

  vpc_security_group_ids = [aws_security_group.worker_sg.id]

  dynamic "iam_instance_profile" {
    for_each = var.is_local ? [] : [1]
    content {
      name = var.iam_instance_profile_name
    }
  }

  user_data = base64encode(<<-EOF
#!/bin/bash
set -e
exec > >(tee -a /var/log/user_data.log /var/log/cloud-init-output.log) 2>&1
echo "=== Inicializando no Worker SQLArena (Processamento SQS) ==="

# 0. Verificacao de Golden AMI: Se PostgreSQL local e venv ja existirem, inicializa em ~15s
if [ -d "/opt/sqlarena" ] && [ -f "/opt/sqlarena/app/.venv/bin/python" ]; then
    echo "=== [Golden AMI Detectada] PostgreSQL e Worker ja configurados! ==="
    cat <<EOT > /opt/sqlarena/app/.env
ENVIRONMENT=production
SANDBOX_DATABASE_URL=postgresql://sandbox:sandboxpass@localhost:5432/sandbox_db
BACKEND_INTERNAL_URL=http://${aws_lb.api_alb.dns_name}
INTERNAL_API_KEY=sqlarena-internal-service-secret-key-32chars

AWS_REGION=${var.aws_region}
S3_BUCKET_NAME=${var.s3_bucket_name}
SQS_QUEUE_NAME=${aws_sqs_queue.submissions_queue.name}
SQS_DLQ_NAME=${aws_sqs_queue.submissions_dlq.name}
EOT

    sudo systemctl restart postgresql || sudo systemctl start postgresql
    sudo systemctl daemon-reload
    sudo systemctl enable sqlarena-worker.service
    sudo systemctl restart sqlarena-worker.service
    echo "=== Worker SQLArena inicializado com sucesso via Golden AMI em ~15s ==="
    exit 0
fi

# 1. Atualizar SO e instalar dependencias (incluindo PostgreSQL local para Sandbox)
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git python3 python3-pip python3-venv libpq-dev postgresql postgresql-contrib

# 2. Inicializar e configurar PostgreSQL Local na EC2 do Worker
sudo systemctl enable postgresql
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE USER sandbox WITH PASSWORD 'sandboxpass';" || true
sudo -u postgres psql -c "CREATE DATABASE sandbox_db OWNER sandbox;" || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE sandbox_db TO sandbox;" || true

# 3. Clonar repositorio
sudo mkdir -p /opt/sqlarena
cd /opt
sudo rm -rf sqlarena
git clone -b ${var.github_branch} ${var.github_repo_url} /opt/sqlarena
cd /opt/sqlarena

# 4. Preparar virtualenv Python e dependencias
python3 -m venv app/.venv
source app/.venv/bin/activate
pip install --upgrade pip
pip install -r app/requirements.txt

# 5. Escrever arquivo de configuracao app/.env (100% Desacoplado de RDS e Redis)
cat <<EOT > app/.env
ENVIRONMENT=production
SANDBOX_DATABASE_URL=postgresql://sandbox:sandboxpass@localhost:5432/sandbox_db
BACKEND_INTERNAL_URL=http://${aws_lb.api_alb.dns_name}
INTERNAL_API_KEY=sqlarena-internal-service-secret-key-32chars

AWS_REGION=${var.aws_region}
S3_BUCKET_NAME=${var.s3_bucket_name}
SQS_QUEUE_NAME=${aws_sqs_queue.submissions_queue.name}
SQS_DLQ_NAME=${aws_sqs_queue.submissions_dlq.name}
EOT

# 5. Criar servico systemd para o Worker Python
cat <<EOT | sudo tee /etc/systemd/system/sqlarena-worker.service
[Unit]
Description=SQLArena SQS Submission Worker
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sqlarena
EnvironmentFile=/opt/sqlarena/app/.env
ExecStart=/opt/sqlarena/app/.venv/bin/python app/worker/main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOT

sudo systemctl daemon-reload
sudo systemctl enable sqlarena-worker.service
sudo systemctl restart sqlarena-worker.service

echo "=== No Worker SQLArena inicializado com sucesso ==="
EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${var.project_name}-worker-node"
      Role = "SandboxWorker"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Auto Scaling Group (ASG 2): Mínimo 1, Máximo 3
resource "aws_autoscaling_group" "worker_asg" {
  name                = "${var.project_name}-worker-asg"
  min_size            = 1
  max_size            = 3
  desired_capacity    = 1
  vpc_zone_identifier = [aws_subnet.public_1.id, aws_subnet.public_2.id]

  health_check_type         = "EC2"
  health_check_grace_period = 180

  launch_template {
    id      = aws_launch_template.worker_lt.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-worker-instance"
    propagate_at_launch = true
  }
}

# Política de Escala: Adiciona 1 instância quando houver acúmulo de mensagens na SQS (Apenas na Nuvem AWS)
resource "aws_autoscaling_policy" "scale_out_workers" {
  count                  = var.is_local ? 0 : 1
  name                   = "scale-out-on-sqs-backlog"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 180
  autoscaling_group_name = aws_autoscaling_group.worker_asg.name
}

# Alarme CloudWatch: SQS com 5 ou mais mensagens visíveis -> Sobe instância (Apenas na Nuvem AWS)
resource "aws_cloudwatch_metric_alarm" "sqs_high_backlog" {
  count               = var.is_local ? 0 : 1
  alarm_name          = "${var.project_name}-sqs-high-backlog"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Gatilha Scale-Out do ASG de Workers se a fila acumular 5+ mensagens"

  dimensions = {
    QueueName = var.sqs_queue_name
  }

  alarm_actions = [aws_autoscaling_policy.scale_out_workers[0].arn]
}

# Política de Escala: Remove instância quando a fila esvaziar (Apenas na Nuvem AWS)
resource "aws_autoscaling_policy" "scale_in_workers" {
  count                  = var.is_local ? 0 : 1
  name                   = "scale-in-on-sqs-empty"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 180
  autoscaling_group_name = aws_autoscaling_group.worker_asg.name
}

# Alarme CloudWatch: SQS vazia (< 1 mensagem) -> Reduz capacidade (Apenas na Nuvem AWS)
resource "aws_cloudwatch_metric_alarm" "sqs_low_backlog" {
  count               = var.is_local ? 0 : 1
  alarm_name          = "${var.project_name}-sqs-low-backlog"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 120
  statistic           = "Sum"
  threshold           = 1
  alarm_description   = "Gatilha Scale-In do ASG de Workers quando a fila esvaziar"

  dimensions = {
    QueueName = var.sqs_queue_name
  }

  alarm_actions = [aws_autoscaling_policy.scale_in_workers[0].arn]
}