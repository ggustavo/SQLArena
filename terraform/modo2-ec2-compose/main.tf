# ==============================================================================
# Stack Isolada - MODO 2: 1 EC2 com Docker e Docker Compose + Amazon DynamoDB
# ==============================================================================
# Você pode executar o Modo 2 diretamente desta pasta (cd terraform/modo2-ec2-compose)
# ou a partir da pasta raiz (cd terraform) usando -var-file="envs/modo2-ec2-compose.tfvars".
# ==============================================================================

terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region     = var.aws_region
  access_key = var.aws_access_key != "" ? var.aws_access_key : null
  secret_key = var.aws_secret_key != "" ? var.aws_secret_key : null
  token      = var.aws_session_token != "" ? var.aws_session_token : null

  default_tags {
    tags = {
      Project    = var.project_name
      DeployMode = "Modo2-EC2-DockerCompose-DynamoDB"
      ManagedBy  = "Terraform"
    }
  }
}

module "dynamodb" {
  source                   = "../modules/dynamodb"
  project_name             = var.project_name
  is_local                 = false
  dynamodb_table_name      = var.dynamodb_table_name
  dynamodb_crud_table_name = var.dynamodb_crud_table_name
}

module "vpc" {
  source       = "../modules/vpc"
  project_name = var.project_name
  aws_region   = var.aws_region
}

module "ec2_compose" {
  source                    = "../modules/ec2-compose"
  project_name              = var.project_name
  vpc_id                    = module.vpc.vpc_id
  subnet_id                 = module.vpc.public_subnet_1_id
  ec2_ami                   = var.ec2_ami
  ec2_instance_type         = var.ec2_instance_type
  iam_instance_profile_name = var.iam_instance_profile_name
  is_local                  = false
  aws_region                = var.aws_region
  dynamodb_table_name       = module.dynamodb.submissions_table_name
  dynamodb_crud_table_name  = module.dynamodb.crud_table_name
  github_repo_url           = var.github_repo_url
  github_branch             = var.github_branch
}
