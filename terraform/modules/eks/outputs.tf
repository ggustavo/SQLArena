output "cluster_name" {
  description = "Nome do cluster EKS"
  value       = aws_eks_cluster.main.name
}

output "cluster_endpoint" {
  description = "Endpoint da API do Kubernetes (EKS)"
  value       = aws_eks_cluster.main.endpoint
}

output "ecr_backend_repository_url" {
  description = "URL do repositório ECR para a imagem do Backend/Worker"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  description = "URL do repositório ECR para a imagem do Frontend"
  value       = aws_ecr_repository.frontend.repository_url
}

output "nodeport_security_group_id" {
  description = "Security Group que libera os NodePorts (30080, 30800, 30901)"
  value       = aws_security_group.eks_nodeport_sg.id
}
