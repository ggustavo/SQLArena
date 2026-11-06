output "instance_id" {
  description = "ID da instância EC2 rodando Docker Compose"
  value       = aws_instance.docker_host.id
}

output "public_ip" {
  description = "IP Público da instância EC2"
  value       = aws_instance.docker_host.public_ip
}

output "public_dns" {
  description = "DNS Público da instância EC2"
  value       = aws_instance.docker_host.public_dns
}

output "frontend_url" {
  description = "URL da Plataforma Web SQLArena (Frontend + API)"
  value       = "http://${aws_instance.docker_host.public_ip}"
}

output "swagger_docs_url" {
  description = "URL da Documentação Swagger UI da API FastAPI"
  value       = "http://${aws_instance.docker_host.public_ip}:8000/docs"
}

output "minio_console_url" {
  description = "URL do Console Web do MinIO (Armazenamento de Arquivos)"
  value       = "http://${aws_instance.docker_host.public_ip}:9001"
}
