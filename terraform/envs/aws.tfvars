# Variáveis para deploy na AWS Real
project_name   = "sqlarena"
environment    = "prod"
is_local       = false
aws_region     = "us-east-1"

# Deixe em branco se suas credenciais já estiverem configuradas via 'aws configure' ou variáveis de ambiente do SO
aws_access_key = ""
aws_secret_key = ""
local_endpoint = ""

# RDS
db_name        = "app_db"
db_username    = "postgres"
db_password    = "substitua_por_uma_senha_forte_em_producao"

# EC2 (Máquina virtual limpa - Ubuntu 22.04 LTS ou Amazon Linux 2023)
ec2_instance_type = "t3.micro"
ec2_ami           = "ami-0c7217cdde317cfec" # Exemplo: Ubuntu 22.04 LTS em us-east-1
app_port          = 8000

# SQS
sqs_queue_name    = "sqlarena-submissions-queue"

