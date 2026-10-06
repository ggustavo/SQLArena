# Security Group do Application Load Balancer (Porta 80 pública)
resource "aws_security_group" "alb_sg" {
  name        = "${var.project_name}-alb-sg"
  description = "Regras de firewall para o Application Load Balancer publico"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Trafego HTTP publico"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Trafego de saida liberado para as instancias do ASG Web"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}

# Security Group do ASG 1 (API FastAPI)
resource "aws_security_group" "web_sg" {
  name        = "${var.project_name}-web-sg"
  description = "Regras de firewall para as instancias FastAPI do ASG 1"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Trafego vindo exclusivamente do Application Load Balancer"
    from_port       = var.app_port
    to_port         = var.app_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  ingress {
    description = "Acesso administrativo SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Trafego de saida liberado"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-web-sg"
  }
}

# Security Group do ASG 2 (Workers de Execução em Sandbox)
# Conforme Requisitos: Não expõe nenhuma porta pública HTTP para a Internet.
resource "aws_security_group" "worker_sg" {
  name        = "${var.project_name}-worker-sg"
  description = "Regras de firewall para os Workers do ASG 2 (Sem portas HTTP publicas)"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Acesso administrativo SSH restrito"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Trafego de saida liberado para SQS, RDS, ElastiCache e S3"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-worker-sg"
  }
}

# Security Group do RDS PostgreSQL (Porta 5432)
resource "aws_security_group" "rds_sg" {
  name        = "${var.project_name}-rds-sg"
  description = "Regras de firewall para o RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Trafego PostgreSQL vindo da Web API"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.web_sg.id]
  }

  ingress {
    description     = "Trafego PostgreSQL vindo dos Workers"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.worker_sg.id]
  }

  egress {
    description = "Trafego de saida liberado"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-rds-sg"
  }
}

# Security Group do ElastiCache Redis (Porta 6379)
resource "aws_security_group" "redis_sg" {
  name        = "${var.project_name}-redis-sg"
  description = "Regras de firewall para o cluster ElastiCache Redis"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Trafego Redis vindo da Web API"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.web_sg.id]
  }

  ingress {
    description     = "Trafego Redis vindo dos Workers"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.worker_sg.id]
  }

  egress {
    description = "Trafego de saida liberado"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-redis-sg"
  }
}
