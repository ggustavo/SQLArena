# ⚔️ SQLArena - Plataforma de Ensino e Avaliação de SQL

Plataforma distribuída para prática e avaliação de consultas SQL em ambiente real **PostgreSQL 16** com isolamento por schemas (Sandbox), avaliação assíncrona desacoplada via **Amazon SQS**, cache de validação via **Redis** e Infraestrutura como Código via **Terraform**.

---

## 🧭 Visão dos Dois Ambientes: Local vs Nuvem AWS

O projeto foi desenhado para funcionar de forma idêntica em dois cenários:

```text
┌───────────────────────────────────────────────┬──────────────────────────────────────────────┐
│        1. AMBIENTE LOCAL (Ministack/Docker)   │       2. NUVEM REAL (AWS Academy Learner Lab) │
├───────────────────────────────────────────────┼──────────────────────────────────────────────┤
│ • Docker Compose: Postgres + Redis + Ministack│ • AWS Gerenciada (RDS, ElastiCache, VPC)     │
│ • Terraform: envs/local.tfvars                │ • Terraform: envs/aws_academy.tfvars         │
│ • Execução: Seu PC roda FastAPI e Workers     │ • Execução: Instâncias EC2 em Duplo ASG      │
└───────────────────────────────────────────────┴──────────────────────────────────────────────┘
```

---

# 💻 TRILHA 1: AMBIENTE LOCAL (Desenvolvimento no seu PC)

Siga este passo a passo para rodar tudo na sua máquina com o emulador local.

### Passo 1: Subir a Infraestrutura Base (Docker)
> ⚠️ Abra o **Docker Desktop** antes de executar.

No terminal na raiz do projeto (`SQLArena/`):
```powershell
docker compose -f ministack/docker-compose.yml up -d
```
*Isso inicia o PostgreSQL 16 (porta 15432), Redis 7 (porta 16379), Ministack AWS (porta 4566) e o painel StackPort (porta 8080).*

---

### Passo 2: Provisionar a Infraestrutura Local via Terraform (IaC)
Navegue até a pasta `terraform/` e aplique os recursos no Ministack:

```powershell
cd terraform
terraform init
terraform apply -var-file="envs/local.tfvars" -auto-approve
cd ..
```
*O Terraform criará no Ministack:*
* Bucket S3 (`sqlarena-questions-bucket`)
* Fila SQS e DLQ (`sqlarena-submissions-queue`)
* Tabelas DynamoDB de submissões e auditoria
* VPC, Subnets, Security Groups e Launch Templates locais
* Registro do RDS PostgreSQL e do Redis ElastiCache

---

### Passo 3: Ativar o Python e Rodar o Seed
Na raiz do projeto (`SQLArena/`), execute no PowerShell:

```powershell
# Ativar o ambiente virtual:
& app/.venv/Scripts/Activate.ps1

# (Se o PowerShell bloquear a execução de scripts, execute antes:)
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# Instalar dependências (apenas na primeira vez):
pip install -r app/requirements.txt

# Popular o banco relacional, subir scripts no S3 e gerar hashes no Redis:
$env:PYTHONPATH="."
python app/database/seed.py
```
> ✅ O seed popula as 12 categorias, os usuários de teste, 21 questões reais com schemas sandbox no PostgreSQL e hashes SHA-256 no Redis.

---

### Passo 4: Ligar o Backend FastAPI (Terminal 1)
Na raiz do projeto (`SQLArena/`), abra um terminal dedicado:

```powershell
& app/.venv/Scripts/Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
* 🌐 **API Rodando em:** [http://localhost:8000](http://localhost:8000)
* 📖 **Documentação Swagger (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
* 🩺 **Health Check:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Passo 5: Ligar o Worker SQS (Terminal 2)
Abra um **segundo terminal** na raiz do projeto (`SQLArena/`):

```powershell
& app/.venv/Scripts/Activate.ps1
$env:PYTHONPATH="."
python app/worker/main.py
```
* ⚙️ **Função:** Fica em loop consumindo mensagens da fila SQS `sqlarena-submissions-queue`. Quando uma query é enviada, o Worker a executa em schema isolado do PostgreSQL, compara o hash no Redis e grava no RDS e DynamoDB.

---

### Passo 6: Ligar o Frontend React (Terminal 3)
Abra um **terceiro terminal**, acesse a pasta `frontend`:

```powershell
cd frontend
npm install    # (apenas na primeira vez)
npm run dev
```
* 🚀 **Acesse o sistema no navegador:** **[http://localhost:5173](http://localhost:5173)**

---

### 🔑 Credenciais Prontas para Teste

| Perfil | Email | Senha | Acesso |
| :--- | :--- | :--- | :--- |
| **Aluno** | `aluno@sqlarena.com` | `123456` | Dashboard, Arena de Código Monaco (`Ctrl+Enter`), Histórico em Modal, Pontuação de XP |
| **Instrutor** | `instrutor@sqlarena.com` | `123456` | Painel de Criação de Questões, validação de `ORDER BY`, categorias N:N, Logs de Auditoria |

---

### 🛑 Como Desligar / Destruir o Ambiente Local
1. Dê `Ctrl + C` nos terminais do Frontend, Worker e Backend.
2. Destrua os recursos do Terraform local:
   ```powershell
   cd terraform
   terraform destroy -var-file="envs/local.tfvars" -auto-approve
   cd ..
   ```
3. Destrua os containers Docker e volumes:
   ```powershell
   docker compose -f ministack/docker-compose.yml down -v
   ```

---

# ☁️ TRILHA 2: DEPLOY NA NUVEM (AWS Academy Learner Lab)

Quando você for testar ou apresentar o projeto na sua conta da **AWS Academy**:

### 1. Obter as Credenciais no AWS Academy
1. Entre no seu **AWS Academy Learner Lab** e clique no botão verde **Start Lab**.
2. Quando a bolinha ficar verde, clique no botão **AWS Details**.
3. Na seção **AWS CLI**, copie os três valores temporários:
   * `aws_access_key_id`
   * `aws_secret_access_key`
   * `aws_session_token`

---

### 2. Configurar o Arquivo de Variáveis
Abra o arquivo [`terraform/envs/aws_academy.tfvars`](terraform/envs/aws_academy.tfvars) e cole suas chaves:

```hcl
aws_access_key    = "COLE_AQUI_SEU_AWS_ACCESS_KEY_ID"
aws_secret_key    = "COLE_AQUI_SEU_AWS_SECRET_ACCESS_KEY"
aws_session_token = "COLE_AQUI_SEU_AWS_SESSION_TOKEN"

# Ajuste o nome do bucket para ser único no mundo (ex: seu nome):
s3_bucket_name    = "sqlarena-questions-bucket-academy-gustavo"
```

---

### 3. Executar o Provisionamento no AWS Academy
No terminal dentro da pasta `terraform/`:

```powershell
cd terraform

# 1. Inicializar os provedores:
terraform init

# 2. Conferir o plano de recursos:
terraform plan -var-file="envs/aws_academy.tfvars"

# 3. Aplicar e subir a infraestrutura completa na nuvem:
terraform apply -var-file="envs/aws_academy.tfvars"
```

---

### 4. O Que o Terraform Cria na AWS Real:
* 🌐 **VPC Própria:** Rede isolada com subnets públicas e privadas em zonas distintas (`us-east-1a` e `us-east-1b`), Internet Gateway e Route Tables.
* ⚖️ **Application Load Balancer (ALB):** Ponto de entrada HTTP público balanceando o tráfego entre as instâncias da API.
* 📈 **ASG 1 (API Web FastAPI):** Auto Scaling Group de instâncias EC2 com **Target Tracking** na CPU (mantendo média de 50%, com alarmes de scale-out > 70% e scale-in < 25%).
* ⚡ **ASG 2 (Workers Sandbox):** Auto Scaling Group de instâncias EC2 com políticas de escala baseadas na métrica `ApproximateNumberOfMessagesVisible` da fila SQS.
* 🗄️ **AWS RDS PostgreSQL:** Banco de dados relacional gerenciado para metadados e pontuação.
* 🏎️ **AWS ElastiCache Redis:** Cluster em memória gerenciado para rate limit (5s) e hashes SHA-256.
* 🪣 **Amazon S3:** Bucket com scripts SQL puros de cada questão.
* 📬 **Amazon SQS:** Fila com Dead Letter Queue (DLQ) para mensageria assíncrona.
* 📄 **Amazon DynamoDB:** Tabelas NoSQL imutáveis para histórico de execuções e auditoria.

---

### 5. Destruir os Recursos no AWS Academy (Evitar Gastar Créditos)
Ao terminar seus testes no Learner Lab, destrua toda a infraestrutura para não consumir seu orçamento de créditos da AWS:

```powershell
terraform destroy -var-file="envs/aws_academy.tfvars"
```

---

## 🧪 Suíte de Testes Automatizados (pytest)

Com a infraestrutura ativa (local ou nuvem):

```powershell
$env:PYTHONPATH="."
pytest app/testes/test_api.py app/testes/test_worker_e2e.py app/testes/test_e2e_full.py -v
```

Scripts de teste individuais de cada serviço AWS:
```powershell
python app/testes/main_s3.py
python app/testes/main_sqs.py
python app/testes/main_dynamodb.py
```
