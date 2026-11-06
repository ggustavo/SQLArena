output "ec2_public_ip" {
  description = "IP Público da instância EC2"
  value       = module.ec2_compose.public_ip
}

output "frontend_url" {
  description = "URL da Plataforma SQLArena (Frontend + API)"
  value       = module.ec2_compose.frontend_url
}

output "swagger_docs_url" {
  description = "URL da Documentação Swagger UI (/docs)"
  value       = module.ec2_compose.swagger_docs_url
}

output "minio_console_url" {
  description = "URL do Console Web do MinIO"
  value       = module.ec2_compose.minio_console_url
}

output "dynamodb_submissions_table" {
  description = "Tabela DynamoDB de submissões"
  value       = module.dynamodb.submissions_table_name
}

output "dynamodb_crud_table" {
  description = "Tabela DynamoDB de auditoria CRUD"
  value       = module.dynamodb.crud_table_name
}
