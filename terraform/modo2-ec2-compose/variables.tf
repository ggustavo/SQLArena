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

variable "ec2_instance_type" {
  type    = string
  default = "t3.medium"
}

variable "ec2_ami" {
  type    = string
  default = "ami-0c7217cdde317cfec"
}

variable "iam_instance_profile_name" {
  type    = string
  default = "LabInstanceProfile"
}

variable "github_repo_url" {
  type    = string
  default = "https://github.com/ggustavo/SQLArena.git"
}

variable "github_branch" {
  type    = string
  default = "main"
}
