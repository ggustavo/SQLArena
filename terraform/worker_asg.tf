# Security Group dos Workers (Acesso apenas interno)
resource "aws_security_group" "worker_sg" {
  name        = "${var.project_name}-worker-sg"
  description = "Regras de firewall para as instancias EC2 dos Workers de execucao"

  egress {
    description = "Acesso de saida para VPC/Internet (SQS, DynamoDB, RDS, Redis)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-worker-sg"
  }
}

# Launch Template do Worker (AMI e configuracoes de boot)
resource "aws_launch_template" "worker_lt" {
  name_prefix   = "${var.project_name}-worker-lt-"
  image_id      = var.ec2_ami
  instance_type = var.ec2_instance_type

  vpc_security_group_ids = [aws_security_group.worker_sg.id]

  # Script de inicializacao para subir o worker em systemd
  user_data = base64encode(<<-EOF
              #!/bin/bash
              echo "Instalando dependencias e iniciando worker..."
              # python3 /app/worker/worker_service.py &
              EOF
  )

  tags = {
    Name = "${var.project_name}-worker-node"
  }
}

# Auto Scaling Group (ASG 2): Minimo 1, Maximo 3
resource "aws_autoscaling_group" "worker_asg" {
  name                = "${var.project_name}-worker-asg"
  min_size            = 1
  max_size            = 3
  desired_capacity    = 1
  availability_zones  = ["${var.aws_region}a", "${var.aws_region}b"]

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

# Politica de Escala: Adiciona 1 instancia quando houver muitas mensagens
resource "aws_autoscaling_policy" "scale_out_workers" {
  name                   = "scale-out-on-sqs-backlog"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 60
  autoscaling_group_name = aws_autoscaling_group.worker_asg.name
}

# Politica de Escala: Remove instancia quando a fila esvaziar
resource "aws_autoscaling_policy" "scale_in_workers" {
  name                   = "scale-in-on-sqs-empty"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 60
  autoscaling_group_name = aws_autoscaling_group.worker_asg.name
}

# Alarme CloudWatch: SQS com mais de 5 mensagens visiveis -> Sobe instancia
resource "aws_cloudwatch_metric_alarm" "sqs_high_backlog" {
  alarm_name          = "${var.project_name}-sqs-high-backlog"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Average"
  threshold           = 5
  alarm_description   = "Gatilha Scale-Out do ASG de Workers se a fila acumular 5+ mensagens"

  dimensions = {
    QueueName = aws_sqs_queue.submissions_queue.name
  }

  alarm_actions = [aws_autoscaling_policy.scale_out_workers.arn]
}