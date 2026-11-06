# ==============================================================================
# Módulo Modo 1: 100% Amazon EKS (Kubernetes) + ECR + AWS DynamoDB
# ==============================================================================
# Provisiona o Cluster Kubernetes gerenciado (Amazon EKS), os repositórios de
# imagens Docker (Amazon ECR) para Backend e Frontend, e o Managed Node Group
# utilizando a IAM Role existente (LabRole no AWS Academy) para acesso nativo
# ao Amazon DynamoDB.
# ==============================================================================

data "aws_iam_role" "eks_role" {
  name = var.iam_role_name
}

# 1. Repositórios Amazon ECR para armazenar as imagens Docker do Backend e Frontend
resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  tags = {
    Name = "${var.project_name}-backend-ecr"
  }
}

resource "aws_ecr_repository" "frontend" {
  name                 = "${var.project_name}-frontend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  tags = {
    Name = "${var.project_name}-frontend-ecr"
  }
}

# 2. Security Group adicional para permitir acesso aos Services NodePort do Kubernetes
# - 30080: Pod Web (Frontend React + Nginx Reverse Proxy)
# - 30800: Pod Web (API FastAPI Direta)
# - 30901: Console Web do MinIO
resource "aws_security_group" "eks_nodeport_sg" {
  name        = "${var.project_name}-eks-nodeport-sg"
  description = "Libera portas NodePort (30080, 30800, 30901) para acesso externo aos Pods K8s"
  vpc_id      = var.vpc_id

  ingress {
    description = "NodePort 30080 - Frontend + API (sqlarena-web-nodeport)"
    from_port   = 30080
    to_port     = 30080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "NodePort 30800 - API FastAPI Direta"
    from_port   = 30800
    to_port     = 30800
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "NodePort 30901 - Console Web do MinIO"
    from_port   = 30901
    to_port     = 30901
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Comunicacao interna entre nos do cluster"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    description = "Saida liberada (incluindo comunicacao com AWS DynamoDB e ECR)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-eks-nodeport-sg"
  }
}

# 3. Cluster Amazon EKS
resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = data.aws_iam_role.eks_role.arn
  version  = "1.29"

  vpc_config {
    subnet_ids              = var.subnet_ids
    security_group_ids      = [aws_security_group.eks_nodeport_sg.id]
    endpoint_public_access  = true
    endpoint_private_access = true
  }

  tags = {
    Name = var.cluster_name
    Mode = "Modo1-EKS"
  }
}

# Regra explícita no Cluster Security Group do EKS liberando portas NodePort (30000-32767) nos Worker Nodes
resource "aws_security_group_rule" "eks_cluster_nodeport_ingress" {
  type              = "ingress"
  from_port         = 30000
  to_port           = 32767
  protocol          = "tcp"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_eks_cluster.main.vpc_config[0].cluster_security_group_id
  description       = "Permite acesso externo aos Services NodePort do Kubernetes (30080 Web, 30800 API, 30901 MinIO)"
}

# 4. Managed Node Group (Worker Nodes onde rodam os Pods do SQLArena)
resource "aws_eks_node_group" "nodes" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.project_name}-node-group"
  node_role_arn   = data.aws_iam_role.eks_role.arn
  subnet_ids      = var.subnet_ids
  instance_types  = [var.node_instance_type]
  disk_size       = 30

  scaling_config {
    desired_size = var.desired_nodes
    min_size     = var.min_nodes
    max_size     = var.max_nodes
  }

  update_config {
    max_unavailable = 1
  }

  tags = {
    Name = "${var.project_name}-eks-node-group"
  }
}
