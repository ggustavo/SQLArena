# ==============================================================================
# Configurações para Deploy no AWS Academy (Learner Lab)
# ==============================================================================
project_name      = "sqlarena"
environment       = "academy"
is_local          = false
aws_region        = "us-east-1"

# ------------------------------------------------------------------------------
# Credenciais do AWS Academy Learner Lab
# No console do Learner Lab, clique em "AWS Details" -> "AWS CLI"
# e cole os valores correspondentes abaixo:
# ------------------------------------------------------------------------------
aws_access_key    = "COLE_AQUI_SEU_AWS_ACCESS_KEY_ID"
aws_secret_key    = "COLE_AQUI_SEU_AWS_SECRET_ACCESS_KEY"
aws_session_token = "COLE_AQUI_SEU_AWS_SESSION_TOKEN"
local_endpoint    = ""

# Banco de Dados RDS PostgreSQL
db_name           = "app_db"
db_username       = "postgres"
db_password       = "SqlArena2026MasterKey!"

# EC2 e Launch Templates (Ubuntu 22.04 LTS em us-east-1 suportado pelo AWS Academy)
ec2_instance_type = "t3.micro"
ec2_ami           = "ami-0c7217cdde317cfec"
app_port          = 8000

# Amazon SQS
sqs_queue_name    = "sqlarena-submissions-queue"

# Amazon S3 (Atenção: nome do bucket na AWS deve ser único globalmente)
s3_bucket_name    = "sqlarena-questions-bucket-academy-gustavo"

# Amazon DynamoDB
dynamodb_table_name      = "sqlarena-submissions-log"
dynamodb_crud_table_name = "sqlarena-crud-actions-log"
