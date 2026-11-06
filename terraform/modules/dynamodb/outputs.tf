output "submissions_table_name" {
  description = "Nome da tabela DynamoDB de submissões"
  value       = aws_dynamodb_table.submissions_log.name
}

output "submissions_table_arn" {
  description = "ARN da tabela DynamoDB de submissões"
  value       = aws_dynamodb_table.submissions_log.arn
}

output "crud_table_name" {
  description = "Nome da tabela DynamoDB de auditoria CRUD"
  value       = aws_dynamodb_table.crud_actions_log.name
}

output "crud_table_arn" {
  description = "ARN da tabela DynamoDB de auditoria CRUD"
  value       = aws_dynamodb_table.crud_actions_log.arn
}
