variable "project_name" {
  type    = string
  default = "sqlarena"
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "aws_access_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "aws_secret_key" {
  type      = string
  default   = ""
  sensitive = true
}

variable "aws_session_token" {
  type      = string
  default   = ""
  sensitive = true
}

variable "dynamodb_table_name" {
  type    = string
  default = "sqlarena-submissions-log"
}

variable "dynamodb_crud_table_name" {
  type    = string
  default = "sqlarena-crud-actions-log"
}

variable "eks_cluster_name" {
  type    = string
  default = "sqlarena-eks"
}

variable "iam_role_name" {
  type    = string
  default = "LabRole"
}

variable "eks_node_instance_type" {
  type    = string
  default = "t3.medium"
}

variable "eks_desired_nodes" {
  type    = number
  default = 2
}

variable "eks_min_nodes" {
  type    = number
  default = 1
}

variable "eks_max_nodes" {
  type    = number
  default = 4
}
