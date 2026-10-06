# ASG 1: API FastAPI (Camada Web / ASG 1)
# Launch Template para as instâncias da API Web
resource "aws_launch_template" "web_lt" {
  name_prefix   = "${var.project_name}-web-"
  image_id      = var.ec2_ami
  instance_type = var.ec2_instance_type

  vpc_security_group_ids = [aws_security_group.web_sg.id]

  user_data = base64encode(<<-EOF
              #!/bin/bash
              set -e
              echo "Inicializando nó da API Web FastAPI..."
              sudo apt-get update -y && sudo apt-get install -y python3-pip git
              cd /opt
              # Inicia o serviço da API FastAPI via uvicorn
              # uvicorn app.main:app --host 0.0.0.0 --port ${var.app_port} --workers 4
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
