# ==============================================================================
# Configurações para Deploy no AWS Academy (Learner Lab)
# ==============================================================================
project_name      = "sqlarena"
environment       = "academy"
is_local          = false
aws_region        = "us-east-1"

# ------------------------------------------------------------------------------
# As credenciais da AWS devem ser colocadas em 'terraform/credentials.auto.tfvars'
# Esse arquivo está protegido pelo .gitignore e o Terraform o carrega automaticamente!
# ------------------------------------------------------------------------------
local_endpoint    = ""

# Banco de Dados RDS PostgreSQL
db_name           = "app_db"
db_username       = "postgres"
db_password       = "SqlArena2026MasterKey!"

# EC2 e Launch Templates (Ubuntu 22.04 LTS em us-east-1 suportado pelo AWS Academy)
ec2_instance_type = "t3.micro"
ec2_ami           = "ami-0c7217cdde317cfec" # AMI Ubuntu 22.04 base pública
app_port          = 8000

# Golden AMIs (Carregadas automaticamente via amis.auto.tfvars gerado pelo builder)
# Se amis.auto.tfvars nao existir, o Terraform usara a ec2_ami base publica.
# web_ami    = ""
# worker_ami = ""

# Amazon SQS
sqs_queue_name    = "sqlarena-submissions-queue"

# Amazon S3 (Atenção: nome do bucket na AWS deve ser único globalmente)
s3_bucket_name    = "sqlarena-questions-bucket-academy-gustavo"

# Amazon DynamoDB
dynamodb_table_name      = "sqlarena-submissions-log"
dynamodb_crud_table_name = "sqlarena-crud-actions-log"
