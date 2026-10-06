# Application Load Balancer
output "alb_dns_name" {
  description = "DNS público do Application Load Balancer (Ponto de entrada da API)"
  value       = aws_lb.api_alb.dns_name
}

output "alb_arn" {
  description = "ARN do Application Load Balancer"
  value       = aws_lb.api_alb.arn
}

output "api_target_group_arn" {
  description = "ARN do Target Group da API FastAPI"
  value       = aws_lb_target_group.api_tg.arn
}

# Auto Scaling Groups
output "asg_web_name" {
  description = "Nome do Auto Scaling Group da Camada Web (FastAPI)"
  value       = aws_autoscaling_group.web_asg.name
}

output "asg_worker_name" {
  description = "Nome do Auto Scaling Group dos Workers de Execução em Sandbox"
  value       = aws_autoscaling_group.worker_asg.name
}

# RDS PostgreSQL
output "rds_endpoint" {
  description = "Endpoint de conexão com o banco RDS"
  value       = aws_db_instance.postgres.endpoint
}

output "rds_address" {
  description = "Host / endereço do banco RDS"
  value       = aws_db_instance.postgres.address
}

output "rds_port" {
  description = "Porta do banco RDS"
  value       = aws_db_instance.postgres.port
}

# ElastiCache Redis
output "elasticache_cluster_id" {
  description = "Identificador do cluster ElastiCache Redis"
  value       = aws_elasticache_cluster.redis.cluster_id
}

output "elasticache_port" {
  description = "Porta de conexão do Redis"
  value       = aws_elasticache_cluster.redis.port
}

# SQS Queues
output "sqs_queue_url" {
  description = "URL da fila principal do SQS"
  value       = aws_sqs_queue.submissions_queue.url
}

output "sqs_queue_arn" {
  description = "ARN da fila principal do SQS"
  value       = aws_sqs_queue.submissions_queue.arn
}

output "sqs_dlq_url" {
  description = "URL da fila Dead Letter Queue (DLQ)"
  value       = aws_sqs_queue.submissions_dlq.url
}

# S3 Bucket
output "s3_bucket_name" {
  description = "Nome do bucket S3 das questões"
  value       = aws_s3_bucket.questions_bucket.id
}

output "s3_bucket_arn" {
  description = "ARN do bucket S3 das questões"
  value       = aws_s3_bucket.questions_bucket.arn
}

# DynamoDB Tables
output "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB de logs de submissão"
  value       = aws_dynamodb_table.submissions_log.name
}

output "dynamodb_table_arn" {
  description = "ARN da tabela DynamoDB de logs de submissão"
  value       = aws_dynamodb_table.submissions_log.arn
}

output "dynamodb_crud_table_name" {
  description = "Nome da tabela DynamoDB de log de ações de CRUD"
  value       = aws_dynamodb_table.crud_actions_log.name
}

output "dynamodb_crud_table_arn" {
  description = "ARN da tabela DynamoDB de log de ações de CRUD"
  value       = aws_dynamodb_table.crud_actions_log.arn
}
