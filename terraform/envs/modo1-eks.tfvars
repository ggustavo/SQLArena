# ==============================================================================
# MODO 1: 100% Amazon EKS (Kubernetes) + Amazon DynamoDB na AWS
# ==============================================================================
# Como aplicar:
#   cd terraform
#   terraform init
#   terraform apply -var-file="envs/modo1-eks.tfvars" -var-file="envs/credentials.tfvars"
# ==============================================================================

project_name             = "sqlarena"
environment              = "eks-aws"
deploy_mode              = "eks"
is_local                 = false
aws_region               = "us-east-1"

# Amazon DynamoDB (Mantido gerenciado na AWS)
dynamodb_table_name      = "sqlarena-submissions-log"
dynamodb_crud_table_name = "sqlarena-crud-actions-log"

# Configurações do Cluster Amazon EKS
eks_cluster_name         = "sqlarena-eks"
iam_role_name            = "LabRole"
eks_node_instance_type   = "t3.medium"
eks_desired_nodes        = 2
eks_min_nodes            = 1
eks_max_nodes            = 4
