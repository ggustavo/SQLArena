variable "project_name" {
  description = "Nome base do projeto"
  type        = string
  default     = "sqlarena"
}

variable "vpc_id" {
  description = "ID da VPC"
  type        = string
}

variable "subnet_id" {
  description = "ID da Sub-rede Pública onde a EC2 será provisionada"
  type        = string
}

variable "ec2_ami" {
  description = "ID da AMI Ubuntu 22.04 LTS em us-east-1"
  type        = string
  default     = "ami-0c7217cdde317cfec"
}

variable "ec2_instance_type" {
  description = "Tipo da instância EC2 (recomendado t3.medium para rodar todos os containers com folga)"
  type        = string
  default     = "t3.medium"
}

variable "iam_instance_profile_name" {
  description = "IAM Instance Profile para acesso automático ao DynamoDB (LabInstanceProfile no AWS Academy)"
  type        = string
  default     = "LabInstanceProfile"
}

variable "is_local" {
  description = "Se está rodando em emulador local"
  type        = bool
  default     = false
}

variable "aws_region" {
  description = "Região da AWS"
  type        = string
  default     = "us-east-1"
}

variable "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB de submissões"
  type        = string
  default     = "sqlarena-submissions-log"
}

variable "dynamodb_crud_table_name" {
  description = "Nome da tabela DynamoDB de auditoria CRUD"
  type        = string
  default     = "sqlarena-crud-actions-log"
}

variable "github_repo_url" {
  description = "URL do repositório Git para clone automático no boot da EC2"
  type        = string
  default     = "https://github.com/ggustavo/SQLArena.git"
}

variable "github_branch" {
  description = "Branch do repositório Git"
  type        = string
  default     = "main"
}
