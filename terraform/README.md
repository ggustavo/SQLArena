# 🏗️ Organização do Terraform - SQLArena

Esta pasta contém toda a Infraestrutura como Código (IaC) modularizada para implantar o **SQLArena** na AWS mantendo o **Amazon DynamoDB** como serviço gerenciado e rodando os demais serviços (**PostgreSQL**, **MinIO**, **Kafka**, **Redis**, **Backend**, **Worker** e **Frontend**) em containers!

---

## 📂 Estrutura de Pastas

```text
terraform/
├── envs/
│   ├── credentials.tfvars.example   # Modelo para suas credenciais AWS / AWS Academy
│   ├── modo1-eks.tfvars             # Variáveis para o Modo 1 (100% EKS + DynamoDB)
│   ├── modo2-ec2-compose.tfvars     # Variáveis para o Modo 2 (1 EC2 com Docker Compose + DynamoDB)
│   └── local.tfvars                 # Variáveis para emulador local (Ministack)
├── modules/                         # Módulos reutilizáveis
│   ├── dynamodb/                    # Tabelas NoSQL no AWS DynamoDB (submissões e auditoria CRUD)
│   ├── vpc/                         # Rede VPC, Internet Gateway e Sub-redes públicas (AZ a e b)
│   ├── eks/                         # Cluster Amazon EKS, Node Group, ECR e Security Group NodePort
│   └── ec2-compose/                 # 1 Instância EC2 com Docker + Docker Compose automático no boot
├── modo1-eks/                       # Stack isolada pronta para rodar o Modo 1
├── modo2-ec2-compose/               # Stack isolada pronta para rodar o Modo 2
├── main.tf                          # Orquestrador raiz que alterna entre Modo 1 e Modo 2 via deploy_mode
├── variables.tf                     # Definição de variáveis
├── outputs.tf                       # Endereços IP, URLs e comandos gerados após o deploy
└── providers.tf                     # Configuração do provedor AWS
```

---

## 🚀 Como Usar os Dois Modos na AWS

### Passo 0: Configurar Credenciais da AWS
Copie `envs/credentials.tfvars.example` para `envs/credentials.tfvars` (protegido pelo `.gitignore`) e cole suas chaves do AWS Academy (`aws_access_key`, `aws_secret_key` e `aws_session_token`).

---

### Opção 1 — Modo 2: Apenas Docker e Docker Compose em 1 EC2 + DynamoDB
Provisiona as tabelas do **DynamoDB** na AWS e **1 única instância EC2 (`t3.medium`)** que instala automaticamente o Docker e o Docker Compose, clona o projeto e executa `docker compose up -d --build`:

```powershell
cd terraform
terraform init
terraform apply -var-file="envs/modo2-ec2-compose.tfvars" -var-file="envs/credentials.tfvars"
```
*(Ou se preferir rodar da pasta isolada: `cd terraform/modo2-ec2-compose`, `terraform init` e `terraform apply -var-file="../envs/credentials.tfvars"`).*

---

### Opção 2 — Modo 1: 100% Amazon EKS (Kubernetes) + DynamoDB
Provisiona as tabelas do **DynamoDB**, repositórios **ECR** e o cluster gerenciado **Amazon EKS** com Worker Nodes prontos para receber os manifestos da pasta `k8s/`:

```powershell
cd terraform
terraform init
terraform apply -var-file="envs/modo1-eks.tfvars" -var-file="envs/credentials.tfvars"
```
*(Ou se preferir rodar da pasta isolada: `cd terraform/modo1-eks`, `terraform init` e `terraform apply -var-file="../envs/credentials.tfvars"`).*
