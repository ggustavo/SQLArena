# ==============================================================================
# Módulo DynamoDB: Único serviço de banco de dados mantido gerenciado na AWS
# ==============================================================================

# 1. Tabela de histórico imutável de submissões e diagnósticos do PostgreSQL
resource "aws_dynamodb_table" "submissions_log" {
  name         = var.dynamodb_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "submission_id"

  attribute {
    name = "submission_id"
    type = "S"
  }

  attribute {
    name = "student_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "StudentIndex"
    hash_key        = "student_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.is_local ? false : true
  }

  tags = {
    Name        = var.dynamodb_table_name
    Description = "Log imutavel de submissoes do SQLArena"
  }
}

# 2. Tabela de auditoria de ações administrativas (CRUD de questões e usuários)
resource "aws_dynamodb_table" "crud_actions_log" {
  name         = var.dynamodb_crud_table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "action_id"

  attribute {
    name = "action_id"
    type = "S"
  }

  attribute {
    name = "entity_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "EntityIndex"
    hash_key        = "entity_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = var.is_local ? false : true
  }

  tags = {
    Name        = var.dynamodb_crud_table_name
    Description = "Log imutavel de acoes de CRUD do SQLArena"
  }
}
