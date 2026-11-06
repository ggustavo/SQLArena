variable "project_name" {
  description = "Nome base do projeto para prefixar os recursos"
  type        = string
  default     = "sqlarena"
}

variable "environment" {
  description = "Ambiente de execução (local, ec2-compose, eks)"
  type        = string
  default     = "aws"
}

variable "deploy_mode" {
  description = "Modo de implantação na AWS: 'eks' (Modo 1: 100% EKS + DynamoDB), 'ec2_compose' (Modo 2: 1 EC2 com Docker Compose + DynamoDB) ou 'local' (Apenas DynamoDB local)"
  type        = string
  default     = "ec2_compose"

  validation {
    condition     = contains(["eks", "ec2_compose", "local"], var.deploy_mode)
    error_message = "O deploy_mode deve ser 'eks' (Modo 1), 'ec2_compose' (Modo 2) ou 'local'."
  }
}

variable "is_local" {
  description = "Booleano indicando se o deploy é no ministack local ou na AWS real"
  type        = bool
  default     = false
}

variable "aws_region" {
  description = "Região da AWS"
  type        = string
  default     = "us-east-1"
}

variable "aws_access_key" {
  description = "AWS Access Key"
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
  description = "URL do ministack local (http://127.0.0.1:4566)"
  type        = string
  default     = "http://127.0.0.1:4566"
}

# --- Configurações do Amazon DynamoDB (Mantido na AWS em todos os modos) ---
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

# --- Configurações do Modo 1: Amazon EKS (Kubernetes) ---
variable "eks_cluster_name" {
  description = "Nome do cluster Amazon EKS (Modo 1)"
  type        = string
  default     = "sqlarena-eks"
}

variable "iam_role_name" {
  description = "Nome da IAM Role para o EKS e Node Group (no AWS Academy usar 'LabRole')"
  type        = string
  default     = "LabRole"
}

variable "eks_node_instance_type" {
  description = "Tipo de instância dos nós do EKS (Modo 1)"
  type        = string
  default     = "t3.medium"
}

variable "eks_desired_nodes" {
  description = "Número desejado de nós no cluster EKS"
  type        = number
  default     = 2
}

variable "eks_min_nodes" {
  description = "Número mínimo de nós no cluster EKS"
  type        = number
  default     = 1
}

variable "eks_max_nodes" {
  description = "Número máximo de nós no cluster EKS"
  type        = number
  default     = 4
}

# --- Configurações do Modo 2: 1 EC2 com Docker e Docker Compose ---
variable "ec2_instance_type" {
  description = "Tipo de instância EC2 única para rodar Docker Compose (Modo 2)"
  type        = string
  default     = "t3.medium"
}

variable "ec2_ami" {
  description = "ID da imagem AMI Ubuntu 22.04 LTS em us-east-1"
  type        = string
  default     = "ami-0c7217cdde317cfec"
}

variable "iam_instance_profile_name" {
  description = "Nome do IAM Instance Profile anexado à EC2 (no AWS Academy usar 'LabInstanceProfile')"
  type        = string
  default     = "LabInstanceProfile"
}

variable "github_repo_url" {
  description = "URL do repositório Git para clone automático no boot da EC2 (Modo 2)"
  type        = string
  default     = "https://github.com/ggustavo/SQLArena.git"
}

variable "github_branch" {
  description = "Branch do Git para checkout no boot da EC2 (Modo 2)"
  type        = string
  default     = "main"
}
