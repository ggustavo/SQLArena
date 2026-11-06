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
  access_key = var.is_local ? "test" : (var.aws_access_key != "test" && var.aws_access_key != "" ? var.aws_access_key : null)
  secret_key = var.is_local ? "test" : (var.aws_secret_key != "test" && var.aws_secret_key != "" ? var.aws_secret_key : null)
  token      = var.is_local ? null : (var.aws_session_token != "" ? var.aws_session_token : null)

  skip_credentials_validation = var.is_local
  skip_requesting_account_id  = var.is_local
  skip_metadata_api_check     = var.is_local
  s3_use_path_style           = var.is_local

  dynamic "endpoints" {
    for_each = var.is_local ? [1] : []
    content {
      ec2      = var.local_endpoint
      dynamodb = var.local_endpoint
      iam      = var.local_endpoint
      eks      = var.local_endpoint
      ecr      = var.local_endpoint
    }
  }

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      DeployMode  = var.deploy_mode
      ManagedBy   = "Terraform"
    }
  }
}
