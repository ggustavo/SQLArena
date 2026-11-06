output "eks_cluster_name" {
  description = "Nome do cluster EKS"
  value       = module.eks.cluster_name
}

output "eks_cluster_endpoint" {
  description = "Endpoint do cluster EKS"
  value       = module.eks.cluster_endpoint
}

output "kubeconfig_command" {
  description = "Comando para configurar o kubectl com o cluster EKS"
  value       = "aws eks update-kubeconfig --region ${var.aws_region} --name ${module.eks.cluster_name}"
}

output "ecr_backend_url" {
  description = "Repositório ECR para a imagem do Backend/Worker"
  value       = module.eks.ecr_backend_repository_url
}

output "ecr_frontend_url" {
  description = "Repositório ECR para a imagem do Frontend"
  value       = module.eks.ecr_frontend_repository_url
}

output "dynamodb_submissions_table" {
  description = "Tabela DynamoDB de submissões"
  value       = module.dynamodb.submissions_table_name
}

output "dynamodb_crud_table" {
  description = "Tabela DynamoDB de auditoria CRUD"
  value       = module.dynamodb.crud_table_name
}
