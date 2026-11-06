# ==============================================================================
# Módulo Modo 2: 1 Instância EC2 rodando Docker e Docker Compose + AWS DynamoDB
# ==============================================================================
# Neste modo, todos os containers (Frontend, Backend, Worker, Postgres Principal,
# Postgres Sandbox, MinIO, Kafka e Redis) rodam orquestrados via Docker Compose
# em uma única instância EC2, enquanto os logs imutáveis são gravados no AWS DynamoDB.
# ==============================================================================

resource "aws_security_group" "ec2_compose_sg" {
  name        = "${var.project_name}-ec2-compose-sg"
  description = "Firewall para instancia EC2 unica rodando Docker Compose do SQLArena"
  vpc_id      = var.vpc_id

  ingress {
    description = "HTTP Publico (Frontend React + Nginx Reverse Proxy)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Porta alternativa Frontend (5173)"
    from_port   = 5173
    to_port     = 5173
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "API Backend FastAPI e Swagger UI (/docs)"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Console Web do MinIO (Visualizacao de Buckets e Arquivos SQL)"
    from_port   = 9001
    to_port     = 9001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Acesso administrativo SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Saida liberada (incluindo comunicacao HTTPS com AWS DynamoDB)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ec2-compose-sg"
  }
}

resource "aws_instance" "docker_host" {
  ami                         = var.ec2_ami
  instance_type               = var.ec2_instance_type
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [aws_security_group.ec2_compose_sg.id]
  associate_public_ip_address = true
  iam_instance_profile        = var.is_local ? null : var.iam_instance_profile_name

  root_block_device {
    volume_size           = 30
    volume_type           = "gp3"
    delete_on_termination = true
  }

  user_data = base64encode(<<-EOF
#!/bin/bash
set -e
exec > >(tee -a /var/log/user_data.log /var/log/cloud-init-output.log) 2>&1

echo "=== [Modo 2] Inicializando Host EC2 com Docker e Docker Compose para o SQLArena ==="

# 1. Instalar Docker e Docker Compose Plugin
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y ca-certificates curl gnupg git

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker ubuntu || true

# 2. Clonar repositório do SQLArena
sudo mkdir -p /opt/sqlarena
sudo rm -rf /opt/sqlarena/*
git clone -b ${var.github_branch} ${var.github_repo_url} /opt/sqlarena
cd /opt/sqlarena

# 3. Gerar arquivo .env apontando para as tabelas do AWS DynamoDB
cat <<EOT > /opt/sqlarena/.env
ENVIRONMENT=production
AWS_REGION=${var.aws_region}
DYNAMODB_ENDPOINT_URL=
DYNAMODB_TABLE_NAME=${var.dynamodb_table_name}
DYNAMODB_CRUD_TABLE_NAME=${var.dynamodb_crud_table_name}

POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgrespassword
POSTGRES_DB=app_db

SANDBOX_POSTGRES_USER=sandbox
SANDBOX_POSTGRES_PASSWORD=sandboxpass
SANDBOX_POSTGRES_DB=sandbox_db

MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123
S3_BUCKET_NAME=sqlarena-questions-bucket

KAFKA_TOPIC_NAME=sqlarena-submissions-queue
KAFKA_DLQ_TOPIC_NAME=sqlarena-submissions-queue-dlq
KAFKA_CONSUMER_GROUP=sqlarena-workers-group
EOT

# 4. Construir as imagens e subir todos os containers via Docker Compose
docker compose up -d --build

echo "=== [Modo 2] SQLArena em execução com Docker Compose! ==="
EOF
  )

  tags = {
    Name = "${var.project_name}-docker-compose-ec2"
    Mode = "Modo2-DockerCompose"
  }
}
