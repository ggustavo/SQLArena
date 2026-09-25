# Tabela DynamoDB para log imutável de todas as execuções, submissões e erros
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

  # Índice secundário para consultar histórico de tentativas por aluno ordenadas por data
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
    Description = "Log imutavel de tentativas e execucoes do SQLArena"
  }
}
