output "vpc_id" {
  description = "ID da VPC criada"
  value       = aws_vpc.main.id
}

output "public_subnet_1_id" {
  description = "ID da Sub-rede Pública 1 (AZ a)"
  value       = aws_subnet.public_1.id
}

output "public_subnet_2_id" {
  description = "ID da Sub-rede Pública 2 (AZ b)"
  value       = aws_subnet.public_2.id
}

output "public_subnet_ids" {
  description = "Lista de IDs das sub-redes públicas"
  value       = [aws_subnet.public_1.id, aws_subnet.public_2.id]
}
