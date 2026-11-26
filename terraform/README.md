# 🏗️ Terraform - Módulo Amazon DynamoDB

Módulo de Infraestrutura como Código (IaC) para provisionamento automatizado das tabelas NoSQL do **Amazon DynamoDB** utilizadas pela aplicação SQLArena:
- `sqlarena-submissions-log`: registro imutável do histórico de submissões de consultas SQL;
- `sqlarena-crud-actions-log`: auditoria de ações administrativas (criação, edição e exclusão de questões).

O módulo suporta execução tanto na **nuvem da AWS** quanto em **ambiente local** via Ministack.

---

## 📂 Estrutura

```text
terraform/
├── envs/
│   ├── credentials.tfvars.example   # Modelo para credenciais da AWS (AWS Academy)
│   └── local.tfvars                 # Variáveis para rodar contra o Ministack local (porta 4566)
├── modules/
│   └── dynamodb/                    # Definição das tabelas sqlarena-submissions-log e sqlarena-crud-actions-log
├── main.tf                          # Chamada do módulo dynamodb
├── variables.tf                     # Declaração de variáveis
├── outputs.tf                       # Nomes e ARNs das tabelas criadas
└── providers.tf                     # Provedor AWS oficial (suporta AWS real e Ministack local)
```

---

## 🚀 Como Executar

### Opção A — DynamoDB na AWS Real (AWS Academy)

1. Copie o arquivo de exemplo:
   ```bash
   cp envs/credentials.tfvars.example envs/credentials.tfvars
   ```
2. Abra `envs/credentials.tfvars` e cole seu `aws_access_key`, `aws_secret_key` e `aws_session_token`.
3. Inicialize e aplique:
   ```bash
   cd terraform
   terraform init
   terraform apply -var-file="envs/credentials.tfvars"
   ```

---

### Opção B — DynamoDB Local com Ministack (100% Offline)

1. Inicie o Ministack na pasta `ministack/`:
   ```bash
   docker compose -f ../ministack/docker-compose.yml up -d
   ```
2. Aplique o Terraform apontando para o Ministack local (`http://127.0.0.1:4566`):
   ```bash
   cd terraform
   terraform init
   terraform apply -var-file="envs/local.tfvars"
   ```

---

## 🧹 Destruição das Tabelas

Para destruir as tabelas quando terminar a avaliação:

```bash
cd terraform
terraform destroy -var-file="envs/credentials.tfvars" # Para AWS real
# ou
terraform destroy -var-file="envs/local.tfvars"       # Para Ministack local
```
