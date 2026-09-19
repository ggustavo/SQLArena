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
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key

  # Configurações para funcionamento transparente com o Ministack local
  skip_credentials_validation = var.is_local
  skip_requesting_account_id  = var.is_local
  skip_metadata_api_check     = var.is_local
  s3_use_path_style           = var.is_local

  # Redirecionamento dinâmico dos endpoints para o Ministack quando local
  dynamic "endpoints" {
    for_each = var.is_local ? [1] : []
    content {
      ec2         = var.local_endpoint
      rds         = var.local_endpoint
      elasticache = var.local_endpoint
      sqs         = var.local_endpoint
      ecs         = var.local_endpoint
      ecr         = var.local_endpoint
      iam         = var.local_endpoint
      s3          = var.local_endpoint
    }
  }

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
