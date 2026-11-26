output "submissions_table_name" {
  description = "Nome da tabela DynamoDB de logs de submissão"
  value       = module.dynamodb.submissions_table_name
}

output "submissions_table_arn" {
  description = "ARN da tabela DynamoDB de logs de submissão"
  value       = module.dynamodb.submissions_table_arn
}

output "crud_table_name" {
  description = "Nome da tabela DynamoDB de auditoria de ações de CRUD"
  value       = module.dynamodb.crud_table_name
}

output "crud_table_arn" {
  description = "ARN da tabela DynamoDB de auditoria de ações de CRUD"
  value       = module.dynamodb.crud_table_arn
}
