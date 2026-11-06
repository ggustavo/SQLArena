variable "project_name" {
  description = "Nome base do projeto"
  type        = string
  default     = "sqlarena"
}

variable "cluster_name" {
  description = "Nome do cluster Amazon EKS"
  type        = string
  default     = "sqlarena-eks"
}

variable "vpc_id" {
  description = "ID da VPC"
  type        = string
}

variable "subnet_ids" {
  description = "Lista de IDs das sub-redes para o EKS e Node Group"
  type        = list(string)
}

variable "iam_role_name" {
  description = "Nome da IAM Role existente na AWS (no AWS Academy usar 'LabRole')"
  type        = string
  default     = "LabRole"
}

variable "node_instance_type" {
  description = "Tipo de instância dos Worker Nodes do EKS"
  type        = string
  default     = "t3.medium"
}

variable "desired_nodes" {
  description = "Quantidade desejada de nós no Node Group do EKS"
  type        = number
  default     = 2
}

variable "min_nodes" {
  description = "Quantidade mínima de nós no Node Group do EKS"
  type        = number
  default     = 1
}

variable "max_nodes" {
  description = "Quantidade máxima de nós no Node Group do EKS"
  type        = number
  default     = 4
}
