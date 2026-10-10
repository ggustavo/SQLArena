variable "project_name" {
  description = "Nome base do projeto para prefixar os recursos"
  type        = string
  default     = "sqlarena"
}

variable "environment" {
  description = "Ambiente de execução (local, dev, prod)"
  type        = string
  default     = "local"
}

variable "is_local" {
  description = "Booleano indicando se o deploy é no ministack local ou na AWS"
  type        = bool
  default     = true
}

variable "aws_region" {
  description = "Região da AWS"
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key" {
  description = "AWS Access Key"
  type        = string
  default     = "test"
  sensitive   = true
}

variable "aws_secret_key" {
  description = "AWS Secret Key"
  type        = string
  default     = "test"
  sensitive   = true
}

variable "aws_session_token" {
  description = "AWS Session Token (obrigatório para credenciais temporárias do AWS Academy Learner Lab)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "local_endpoint" {
  description = "URL do ministack local (http://localhost:4566)"
  type        = string
  default     = "http://localhost:4566"
}

# --- Configurações do Banco de Dados (RDS) ---
variable "db_name" {
  description = "Nome do banco de dados inicial no PostgreSQL"
  type        = string
  default     = "app_db"
}

variable "db_username" {
  description = "Usuário master do PostgreSQL"
  type        = string
  default     = "postgres"
}

variable "db_password" {
  description = "Senha do usuário master do PostgreSQL"
  type        = string
  default     = "postgrespassword"
  sensitive   = true
}

# --- Configurações do EC2 (Servidor do Backend) ---
variable "ec2_instance_type" {
  description = "Tipo de instância EC2 (ex: t3.micro)"
  type        = string
  default     = "t3.micro"
}

variable "ec2_ami" {
  description = "ID da imagem AMI padrão para a máquina virtual (Ubuntu 22.04 LTS base)"
  type        = string
  default     = "ami-00000001"
}

variable "web_ami" {
  description = "ID da Golden AMI customizada para o Web (FastAPI + React). Se vazio, usa ec2_ami base."
  type        = string
  default     = ""
}

variable "worker_ami" {
  description = "ID da Golden AMI customizada para o Worker (Postgres Sandbox + Python). Se vazio, usa ec2_ami base."
  type        = string
  default     = ""
}

variable "app_port" {
  description = "Porta liberada no Security Group para a aplicação backend"
  type        = number
  default     = 8000
}

variable "iam_instance_profile_name" {
  description = "Nome do IAM Instance Profile anexado aos nós EC2 (no AWS Academy usar 'LabInstanceProfile')"
  type        = string
  default     = "LabInstanceProfile"
}

# --- Configurações do SQS ---
variable "sqs_queue_name" {
  description = "Nome da fila SQS para processamento assíncrono"
  type        = string
  default     = "sqlarena-submissions-queue"
}

# --- Configurações do S3 ---
variable "s3_bucket_name" {
  description = "Nome do bucket S3 para armazenar os arquivos SQL das questoes"
  type        = string
  default     = "sqlarena-questions-bucket"
}

# --- Configurações do DynamoDB ---
variable "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB para registro imutavel de submissoes"
  type        = string
  default     = "sqlarena-submissions-log"
}

variable "dynamodb_crud_table_name" {
  description = "Nome da tabela DynamoDB para o log de acoes de CRUD (Requisito 5)"
  type        = string
  default     = "sqlarena-crud-actions-log"
}

# --- Configurações de Deploy / Código ---
variable "github_repo_url" {
  description = "URL do repositório Git para clone automático no boot dos nós EC2"
  type        = string
  default     = "https://github.com/ggustavo/SQLArena.git"
}

variable "github_branch" {
  description = "Branch do Git para checkout no boot dos nós EC2"
  type        = string
  default     = "main"
}



