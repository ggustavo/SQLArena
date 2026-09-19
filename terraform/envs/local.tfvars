# Variáveis para execução com Ministack Local
project_name   = "sqlarena"
environment    = "local"
is_local       = true
aws_region     = "us-east-1"
aws_access_key = "test"
aws_secret_key = "test"
local_endpoint = "http://localhost:4566"

# RDS
db_name        = "app_db"
db_username    = "postgres"
db_password    = "postgrespassword"

# EC2 (Máquina virtual limpa)
ec2_instance_type = "t3.micro"
ec2_ami           = "ami-00000001"
app_port          = 8000

# SQS
sqs_queue_name    = "sqlarena-submissions-queue"

