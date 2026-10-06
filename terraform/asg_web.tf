# ASG 1: API FastAPI (Camada Web / ASG 1)
# Launch Template para as instâncias da API Web
resource "aws_launch_template" "web_lt" {
  name_prefix   = "${var.project_name}-web-"
  image_id      = var.ec2_ami
  instance_type = var.ec2_instance_type

  vpc_security_group_ids = [aws_security_group.web_sg.id]

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
echo "=== Inicializando no Web SQLArena (Frontend + Backend FastAPI) ==="

# 1. Atualizar SO e instalar dependencias basicas
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git python3 python3-pip python3-venv curl libpq-dev

# 2. Instalar Node.js LTS (para compilar frontend React)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# 3. Clonar repositorio
sudo mkdir -p /opt/sqlarena
cd /opt
sudo rm -rf sqlarena
git clone -b ${var.github_branch} ${var.github_repo_url} /opt/sqlarena
cd /opt/sqlarena

# 4. Criar virtualenv Python e instalar dependencias
python3 -m venv app/.venv
source app/.venv/bin/activate
pip install --upgrade pip
pip install -r app/requirements.txt

# 5. Escrever arquivo de configuracao app/.env com recursos da AWS
cat <<EOT > app/.env
ENVIRONMENT=production
APP_PORT=${var.app_port}
SECRET_KEY=sqlarena-production-super-secret-key-32chars-min
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

DATABASE_URL=postgresql+psycopg2://${var.db_username}:${var.db_password}@${aws_db_instance.postgres.address}:${aws_db_instance.postgres.port}/${var.db_name}
RDS_HOST=${aws_db_instance.postgres.address}
RDS_PORT=${aws_db_instance.postgres.port}
RDS_USER=${var.db_username}
RDS_PASSWORD=${var.db_password}
RDS_DB_NAME=${var.db_name}

REDIS_URL=redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/0
REDIS_HOST=${aws_elasticache_cluster.redis.cache_nodes[0].address}
REDIS_PORT=6379

AWS_REGION=${var.aws_region}
S3_BUCKET_NAME=${var.s3_bucket_name}
DYNAMO_SUBMISSIONS_TABLE=${aws_dynamodb_table.submissions_log.name}
DYNAMO_CRUD_TABLE_NAME=${aws_dynamodb_table.crud_actions_log.name}
SQS_QUEUE_NAME=${aws_sqs_queue.submissions_queue.name}
SQS_DLQ_NAME=${aws_sqs_queue.submissions_dlq.name}
EOT

# 6. Compilar o Frontend React (Vite SPA)
cd /opt/sqlarena/frontend
export VITE_API_URL=/api
npm install
npm run build

# 7. Executar o seed inicial do banco (tabelas, categorias e 21 questoes no RDS/S3)
cd /opt/sqlarena
python app/database/seed.py || echo "[WARN] Seed ja executado ou aguardando readiness do RDS."

# 8. Criar servico systemd para a API FastAPI + Frontend
cat <<EOT | sudo tee /etc/systemd/system/sqlarena-web.service
[Unit]
Description=SQLArena Web API and Frontend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sqlarena
EnvironmentFile=/opt/sqlarena/app/.env
ExecStart=/opt/sqlarena/app/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port ${var.app_port} --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOT

sudo systemctl daemon-reload
sudo systemctl enable sqlarena-web.service
sudo systemctl restart sqlarena-web.service

echo "=== No Web SQLArena inicializado com sucesso ==="
EOF
  )

  tag_specifications {
    resource_type = "instance"
    tags = {
      Name = "${var.project_name}-web-node"
      Role = "WebAPI"
    }
  }

  lifecycle {
    create_before_destroy = true
  }
}

# Auto Scaling Group para a API FastAPI (1 a 3 instâncias)
resource "aws_autoscaling_group" "web_asg" {
  name                = "${var.project_name}-web-asg"
  min_size            = 1
  max_size            = 3
  desired_capacity    = 1
  vpc_zone_identifier = [aws_subnet.public_1.id, aws_subnet.public_2.id]
  target_group_arns   = [aws_lb_target_group.api_tg.arn]

  health_check_type         = "ELB"
  health_check_grace_period = 300

  launch_template {
    id      = aws_launch_template.web_lt.id
    version = "$Latest"
  }

  tag {
    key                 = "Name"
    value               = "${var.project_name}-web-asg"
    propagate_at_launch = true
  }
}

# Target Tracking Policy de CPU para o ASG 1 (Scale Out > 70%, Scale In < 25%) - Apenas na Nuvem AWS
resource "aws_autoscaling_policy" "web_cpu_target_tracking" {
  count                  = var.is_local ? 0 : 1
  name                   = "${var.project_name}-web-cpu-target-tracking"
  autoscaling_group_name = aws_autoscaling_group.web_asg.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ASGAverageCPUUtilization"
    }
    target_value     = 50.0
    disable_scale_in = false
  }
}

# Políticas e Alarmes explícitos de CPU para Scale Out (> 70%) e Scale In (< 25%) - Apenas na Nuvem AWS
resource "aws_autoscaling_policy" "web_scale_out_policy" {
  count                  = var.is_local ? 0 : 1
  name                   = "${var.project_name}-web-scale-out"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.web_asg.name
}

resource "aws_cloudwatch_metric_alarm" "web_cpu_high" {
  count               = var.is_local ? 0 : 1
  alarm_name          = "${var.project_name}-web-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  statistic           = "Average"
  threshold           = 70

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.web_asg.name
  }

  alarm_actions = [aws_autoscaling_policy.web_scale_out_policy[0].arn]
}

resource "aws_autoscaling_policy" "web_scale_in_policy" {
  count                  = var.is_local ? 0 : 1
  name                   = "${var.project_name}-web-scale-in"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 300
  autoscaling_group_name = aws_autoscaling_group.web_asg.name
}

resource "aws_cloudwatch_metric_alarm" "web_cpu_low" {
  count               = var.is_local ? 0 : 1
  alarm_name          = "${var.project_name}-web-cpu-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  statistic           = "Average"
  threshold           = 25

  dimensions = {
    AutoScalingGroupName = aws_autoscaling_group.web_asg.name
  }

  alarm_actions = [aws_autoscaling_policy.web_scale_in_policy[0].arn]
}
