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

output "elasticache_cluster_id" {
  description = "Identificador do cluster ElastiCache Redis"
  value       = aws_elasticache_cluster.redis.cluster_id
}

output "elasticache_port" {
  description = "Porta de conexão do Redis"
  value       = aws_elasticache_cluster.redis.port
}

output "ec2_instance_id" {
  description = "ID da instância EC2 do backend"
  value       = aws_instance.backend.id
}

output "ec2_public_ip" {
  description = "IP público da máquina EC2"
  value       = aws_instance.backend.public_ip
}

output "ec2_private_ip" {
  description = "IP privado da máquina EC2"
  value       = aws_instance.backend.private_ip
}

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


