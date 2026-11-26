variable "project_name" {
  description = "Nome base do projeto para prefixar os recursos"
  type        = string
  default     = "sqlarena"
}

variable "environment" {
  description = "Ambiente de execução (local ou aws)"
  type        = string
  default     = "local"
}

variable "is_local" {
  description = "Indica se o deploy é no emulador local (Ministack) ou na AWS real"
  type        = bool
  default     = false
}

variable "aws_region" {
  description = "Região da AWS"
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key" {
  description = "AWS Access Key ID"
  type        = string
  default     = ""
  sensitive   = true
}

variable "aws_secret_key" {
  description = "AWS Secret Key"
  type        = string
  default     = ""
  sensitive   = true
}

variable "aws_session_token" {
  description = "AWS Session Token (obrigatório para credenciais temporárias do AWS Academy Learner Lab)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "local_endpoint" {
  description = "URL do endpoint local do Ministack (porta 4566)"
  type        = string
  default     = "http://127.0.0.1:4566"
}

variable "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB para registro imutável de submissões"
  type        = string
  default     = "sqlarena-submissions-log"
}

variable "dynamodb_crud_table_name" {
  description = "Nome da tabela DynamoDB para o log de ações de CRUD"
  type        = string
  default     = "sqlarena-crud-actions-log"
}
