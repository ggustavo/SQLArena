variable "project_name" {
  description = "Nome base do projeto"
  type        = string
  default     = "sqlarena"
}

variable "aws_region" {
  description = "Região da AWS"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Nome do cluster EKS para tags de descoberta de sub-rede"
  type        = string
  default     = "sqlarena-eks"
}
