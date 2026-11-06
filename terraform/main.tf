# ==============================================================================
# Orquestrador Principal do Terraform (Suporta Modo 1 EKS e Modo 2 EC2 Compose)
# ==============================================================================
# Recursos AWS Gerenciados:
# - SEMPRE: Amazon DynamoDB (sqlarena-submissions-log e sqlarena-crud-actions-log)
# - MODO 1 (deploy_mode = "eks"):         VPC + Cluster Amazon EKS + Node Group + ECR
# - MODO 2 (deploy_mode = "ec2_compose"): VPC + 1 Instância EC2 rodando Docker Compose
#
# Obs: RDS, S3, SQS e ElastiCache foram substituídos por containers (Postgres,
# MinIO, Kafka e Redis) rodando dentro do Docker Compose (Modo 2) ou K8s (Modo 1).
# ==============================================================================

# 1. Banco de Dados NoSQL na AWS (Amazon DynamoDB) - Presente em todos os modos
module "dynamodb" {
  source                   = "./modules/dynamodb"
  project_name             = var.project_name
  is_local                 = var.is_local
  dynamodb_table_name      = var.dynamodb_table_name
  dynamodb_crud_table_name = var.dynamodb_crud_table_name
}

# 2. Rede VPC Multi-AZ na AWS (Criada para Modo 1 EKS ou Modo 2 EC2)
module "vpc" {
  count        = var.deploy_mode == "local" ? 0 : 1
  source       = "./modules/vpc"
  project_name = var.project_name
  aws_region   = var.aws_region
  cluster_name = var.eks_cluster_name
}

# 3. MODO 1: 100% Amazon EKS (Kubernetes) + ECR + DynamoDB
module "eks_mode" {
  count              = var.deploy_mode == "eks" ? 1 : 0
  source             = "./modules/eks"
  project_name       = var.project_name
  cluster_name       = var.eks_cluster_name
  vpc_id             = module.vpc[0].vpc_id
  subnet_ids         = module.vpc[0].public_subnet_ids
  iam_role_name      = var.iam_role_name
  node_instance_type = var.eks_node_instance_type
  desired_nodes      = var.eks_desired_nodes
  min_nodes          = var.eks_min_nodes
  max_nodes          = var.eks_max_nodes
}

# 4. MODO 2: Apenas Docker e Docker Compose rodando em 1 EC2 + DynamoDB
module "ec2_compose_mode" {
  count                     = var.deploy_mode == "ec2_compose" ? 1 : 0
  source                    = "./modules/ec2-compose"
  project_name              = var.project_name
  vpc_id                    = module.vpc[0].vpc_id
  subnet_id                 = module.vpc[0].public_subnet_1_id
  ec2_ami                   = var.ec2_ami
  ec2_instance_type         = var.ec2_instance_type
  iam_instance_profile_name = var.iam_instance_profile_name
  is_local                  = var.is_local
  aws_region                = var.aws_region
  dynamodb_table_name       = module.dynamodb.submissions_table_name
  dynamodb_crud_table_name  = module.dynamodb.crud_table_name
  github_repo_url           = var.github_repo_url
  github_branch             = var.github_branch
}
