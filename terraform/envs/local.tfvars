# ==============================================================================
# AMBIENTE LOCAL: Provisiona tabelas DynamoDB no Ministack local (Porta 4566)
# ==============================================================================
project_name             = "sqlarena"
environment              = "local"
is_local                 = true
aws_region               = "us-east-1"
aws_access_key           = "test"
aws_secret_key           = "test"
local_endpoint           = "http://127.0.0.1:4566"

dynamodb_table_name      = "sqlarena-submissions-log"
dynamodb_crud_table_name = "sqlarena-crud-actions-log"
