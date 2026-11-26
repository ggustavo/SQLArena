# ==============================================================================
# SQLArena - Terraform para Amazon DynamoDB (Trabalho 2)
# ==============================================================================
# Conforme a Especificação do Trabalho 2, o DynamoDB é o ÚNICO serviço mantido
# gerenciado na AWS (para armazenamento de histórico de submissões e auditoria CRUD).
# Todos os demais serviços (Postgres, MinIO, Kafka, Redis, Backend, Worker, Frontend)
# rodam como containers locais via Docker Compose ou Kubernetes local.
# ==============================================================================

module "dynamodb" {
  source                   = "./modules/dynamodb"
  project_name             = var.project_name
  is_local                 = var.is_local
  dynamodb_table_name      = var.dynamodb_table_name
  dynamodb_crud_table_name = var.dynamodb_crud_table_name
}
