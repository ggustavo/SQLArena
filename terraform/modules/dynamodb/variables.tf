variable "project_name" {
  description = "Nome base do projeto"
  type        = string
  default     = "sqlarena"
}

variable "is_local" {
  description = "Indica se está rodando em emulador local (Ministack)"
  type        = bool
  default     = false
}

variable "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB para log imutável de submissões"
  type        = string
  default     = "sqlarena-submissions-log"
}

variable "dynamodb_crud_table_name" {
  description = "Nome da tabela DynamoDB para log de auditoria de CRUD"
  type        = string
  default     = "sqlarena-crud-actions-log"
}
