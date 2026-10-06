# ==============================================================================
# ASG 2: Workers de Execução em Sandbox (Camada de Processamento / ASG 2)
# Contribuição de Felipe (feat/sqs-worker-async) integrada à infraestrutura VPC
# ==============================================================================

# Launch Template do Worker (AMI e configurações de boot em Sandbox)
resource "aws_launch_template" "worker_lt" {
  name_prefix   = "${var.project_name}-worker-lt-"
  image_id      = var.ec2_ami
  instance_type = var.ec2_instance_type

  vpc_security_group_ids = [aws_security_group.worker_sg.id]

  user_data = base64encode(<<-EOF
              #!/bin/bash
              set -e
              echo "Instalando dependencias e iniciando worker sandbox PostgreSQL 16..."
              sudo apt-get update -y && sudo apt-get install -y postgresql-16 python3-pip git
              # python3 app/worker/worker_service.py &
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