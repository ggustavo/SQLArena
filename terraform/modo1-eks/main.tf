# ==============================================================================
# Stack Isolada - MODO 1: 100% Amazon EKS (Kubernetes) + Amazon DynamoDB
# ==============================================================================
# Você pode executar o Modo 1 diretamente desta pasta (cd terraform/modo1-eks)
# ou a partir da pasta raiz (cd terraform) usando -var-file="envs/modo1-eks.tfvars".
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
      DeployMode = "Modo1-EKS-DynamoDB"
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
  cluster_name = var.eks_cluster_name
}

module "eks" {
  source             = "../modules/eks"
  project_name       = var.project_name
  cluster_name       = var.eks_cluster_name
  vpc_id             = module.vpc.vpc_id
  subnet_ids         = module.vpc.public_subnet_ids
  iam_role_name      = var.iam_role_name
  node_instance_type = var.eks_node_instance_type
  desired_nodes      = var.eks_desired_nodes
  min_nodes          = var.eks_min_nodes
  max_nodes          = var.eks_max_nodes
}
