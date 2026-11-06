# ==============================================================================
# MODO 2: Apenas Docker e Docker Compose rodando em 1 EC2 + Amazon DynamoDB
# ==============================================================================
# Como aplicar:
#   cd terraform
#   terraform init
#   terraform apply -var-file="envs/modo2-ec2-compose.tfvars" -var-file="envs/credentials.tfvars"
# ==============================================================================

project_name              = "sqlarena"
environment               = "ec2-compose-aws"
deploy_mode               = "ec2_compose"
is_local                  = false
aws_region                = "us-east-1"

# Amazon DynamoDB (Mantido gerenciado na AWS)
dynamodb_table_name       = "sqlarena-submissions-log"
dynamodb_crud_table_name  = "sqlarena-crud-actions-log"

# Instância EC2 Única para rodar todos os containers via Docker Compose
ec2_instance_type         = "t3.medium"
ec2_ami                   = "ami-0c7217cdde317cfec" # Ubuntu 22.04 LTS em us-east-1
iam_instance_profile_name = "LabInstanceProfile"
github_repo_url           = "https://github.com/ggustavo/SQLArena.git"
github_branch             = "main"
