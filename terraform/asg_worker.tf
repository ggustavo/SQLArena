# ASG 2: Workers de Execução em Sandbox (Camada de Processamento / ASG 2)
# Launch Template para os Workers (PostgreSQL 16 local isolado + Python Worker Daemon)
resource "aws_launch_template" "worker_lt" {
  name_prefix   = "${var.project_name}-worker-"
  image_id      = var.ec2_ami
  instance_type = var.ec2_instance_type

  vpc_security_group_ids = [aws_security_group.worker_sg.id]

  user_data = base64encode(<<-EOF
              #!/bin/bash
              set -e
              echo "Inicializando nó de Worker Sandbox PostgreSQL 16..."
              sudo apt-get update -y && sudo apt-get install -y postgresql-16 python3-pip git
              # Inicia o daemon consumidor contínuo da SQS
              # python3 app/worker/main.py
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

# Auto Scaling Group para os Workers (1 a 3 instâncias)
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
    value               = "${var.project_name}-worker-asg"
    propagate_at_launch = true
  }
}

# Política de Scale Out dos Workers baseada na fila SQS (Fila acumulando mensagens)
resource "aws_autoscaling_policy" "worker_scale_out_policy" {
  name                   = "${var.project_name}-worker-scale-out"
  scaling_adjustment     = 1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 180
  autoscaling_group_name = aws_autoscaling_group.worker_asg.name
}

resource "aws_cloudwatch_metric_alarm" "worker_sqs_high" {
  alarm_name          = "${var.project_name}-sqs-messages-high"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 60
  statistic           = "Sum"
  threshold           = 5

  dimensions = {
    QueueName = var.sqs_queue_name
  }

  alarm_actions = [aws_autoscaling_policy.worker_scale_out_policy.arn]
}

# Política de Scale In dos Workers baseada na fila SQS (Fila vazia)
resource "aws_autoscaling_policy" "worker_scale_in_policy" {
  name                   = "${var.project_name}-worker-scale-in"
  scaling_adjustment     = -1
  adjustment_type        = "ChangeInCapacity"
  cooldown               = 180
  autoscaling_group_name = aws_autoscaling_group.worker_asg.name
}

resource "aws_cloudwatch_metric_alarm" "worker_sqs_low" {
  alarm_name          = "${var.project_name}-sqs-messages-low"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 120
  statistic           = "Sum"
  threshold           = 1

  dimensions = {
    QueueName = var.sqs_queue_name
  }

  alarm_actions = [aws_autoscaling_policy.worker_scale_in_policy.arn]
}
