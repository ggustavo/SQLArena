# ==============================================================================
# Outputs do Terraform (Compatível com Modo 1 EKS, Modo 2 EC2 e Local)
# ==============================================================================

output "deploy_mode_ativo" {
  description = "Modo de implantação provisionado"
  value       = var.deploy_mode
}

# --- Outputs do Amazon DynamoDB (Sempre ativos) ---
output "dynamodb_table_name" {
  description = "Nome da tabela DynamoDB de logs de submissão"
  value       = module.dynamodb.submissions_table_name
}

output "dynamodb_crud_table_name" {
  description = "Nome da tabela DynamoDB de log de ações de CRUD"
  value       = module.dynamodb.crud_table_name
}

# --- Outputs do Modo 1: 100% Amazon EKS + DynamoDB ---
output "modo1_eks_cluster_name" {
  description = "[Modo 1 - EKS] Nome do cluster Kubernetes na AWS"
  value       = var.deploy_mode == "eks" ? module.eks_mode[0].cluster_name : null
}

output "modo1_eks_cluster_endpoint" {
  description = "[Modo 1 - EKS] Endpoint da API do cluster EKS"
  value       = var.deploy_mode == "eks" ? module.eks_mode[0].cluster_endpoint : null
}

output "modo1_eks_kubeconfig_command" {
  description = "[Modo 1 - EKS] Comando para conectar seu kubectl local ao cluster EKS na AWS"
  value       = var.deploy_mode == "eks" ? "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks_mode[0].cluster_name}" : null
}

output "modo1_ecr_backend_url" {
  description = "[Modo 1 - EKS] Repositório ECR para push da imagem sqlarena-backend"
  value       = var.deploy_mode == "eks" ? module.eks_mode[0].ecr_backend_repository_url : null
}

output "modo1_ecr_frontend_url" {
  description = "[Modo 1 - EKS] Repositório ECR para push da imagem sqlarena-frontend"
  value       = var.deploy_mode == "eks" ? module.eks_mode[0].ecr_frontend_repository_url : null
}

# --- Outputs do Modo 2: 1 EC2 com Docker Compose + DynamoDB ---
output "modo2_ec2_public_ip" {
  description = "[Modo 2 - EC2 Compose] IP Público da instância EC2 única"
  value       = var.deploy_mode == "ec2_compose" ? module.ec2_compose_mode[0].public_ip : null
}

output "modo2_frontend_url" {
  description = "[Modo 2 - EC2 Compose] URL pública da Plataforma SQLArena (Frontend + API)"
  value       = var.deploy_mode == "ec2_compose" ? module.ec2_compose_mode[0].frontend_url : null
}

output "modo2_swagger_url" {
  description = "[Modo 2 - EC2 Compose] URL do Swagger UI (/docs)"
  value       = var.deploy_mode == "ec2_compose" ? module.ec2_compose_mode[0].swagger_docs_url : null
}

output "modo2_minio_console_url" {
  description = "[Modo 2 - EC2 Compose] URL do Console Web do MinIO (porta 9001)"
  value       = var.deploy_mode == "ec2_compose" ? module.ec2_compose_mode[0].minio_console_url : null
}
