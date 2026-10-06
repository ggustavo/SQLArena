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

---

# 💻 TRILHA 1: AMBIENTE LOCAL (Desenvolvimento no seu PC)

> [!IMPORTANT]
> ### ⚠️ CONCEITO CRUCIAL: Por que preciso rodar o Backend e o Worker em terminais separados no meu PC?
> * **Na AWS Real (Nuvem):** O Terraform cria servidores virtuais **EC2 reais**. Quando as máquinas ligam, a AWS executa automaticamente o script `user_data` configurado no Terraform, que sobe o Backend e o Worker sozinhos sem você precisar tocar em nada.
> * **No seu PC (Ministack Local):** O Ministack é apenas um emulador de APIs. Ele confirma para o Terraform que os recursos existem, mas **ele NÃO cria máquinas virtuais reais** no seu Windows.
> * **A sua máquina física faz o papel das EC2s:** 
>   * O **Terminal 1** (`uvicorn`) faz o papel da EC2 da Camada Web (API).
>   * O **Terminal 2** (`python app/worker/main.py`) faz o papel da EC2 dos Workers.
> * **O que acontece se o Worker não estiver rodando?**
>   Quando você clica em "Executar" no frontend, a FastAPI envia sua consulta para a fila **Amazon SQS**. Se o **Worker não estiver rodando no Terminal 2**, **ninguém consome a fila**, e o frontend fica eternamente em *"Processando..."* ou com status em branco!

---

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

# Popular o banco relacional, validar dinamicamente as 21 questões, subir scripts no S3 e gerar hashes no RDS e Redis:
$env:PYTHONPATH="."
python app/database/seed.py
```
> ✅ O seed valida cada uma das 21 questões em schemas isolados no PostgreSQL via `QuestionValidator`, extrai colunas e tabelas reais, calcula o hash canônico SHA-256, persiste no RDS (`expected_hash`) e no Redis, e cadastra os usuários iniciais com **score 0 e histórico limpo**.

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
| **Aluno** | `aluno@sqlarena.com` | `123456` | Dashboard, Arena Monaco (editor limpo com restauração da última tentativa), Histórico Completo em Modal, Pontuação |
| **Instrutor** | `instrutor@sqlarena.com` | `123456` | Painel com Validação Dinâmica em Sandbox (DDL, DML, `ORDER BY` obrigatório, hash SHA-256 no RDS/Redis), Categorias N:N, Auditoria |

---

### 🖥️ Resumo dos 3 Terminais Necessários no seu Computador

Para testar a plataforma localmente de ponta a ponta, você precisa manter **3 terminais abertos**:

| Terminal | O que roda | Comando | O que faz no sistema |
| :---: | :--- | :--- | :--- |
| **Terminal 1** | **Backend API** | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | Recebe requisições HTTP do frontend e despacha submissões para o SQS |
| **Terminal 2** | **Worker SQS** | `python app/worker/main.py` | **OBRIGATÓRIO:** Consome a fila SQS, roda o SQL no PostgreSQL e avalia a resposta |
| **Terminal 3** | **Frontend SPA** | `cd frontend; npm run dev` | Interface web em React no navegador (`http://localhost:5173`) |

---

### ❓ Perguntas Frequentes & Diagnóstico (Troubleshooting)

#### 1. "Cliquei em 'Executar' na Arena e a tela ficou em 'Processando...' sem sair do lugar ou a fila ficou em branco?"
* **Causa:** O **Worker (Terminal 2)** não está ligado! A consulta foi enviada pelo frontend e colocada na fila SQS, mas ninguém está consumindo a fila.
* **Solução:** Abra o **Terminal 2** com o `.venv` ativo e execute:
  ```powershell
  & app/.venv/Scripts/Activate.ps1
  $env:PYTHONPATH="."
  python app/worker/main.py
  ```
  Assim que o Worker ligar, ele pegará as consultas pendentes na fila imediatamente, executará no PostgreSQL Sandbox e a tela do navegador atualizará em menos de 1 segundo!

#### 2. "O Terraform não deveria ligar as máquinas EC2 e o Worker sozinho?"
* **Na AWS Real:** SIM. O Terraform cria instâncias EC2 gerenciadas pela Amazon e executa o script `user_data` que sobe o worker dentro da máquina virtual.
* **No Computador Local:** NÃO. O Ministack é apenas um emulador de API e não tem poder de criar máquinas virtuais no Windows. No seu computador, a sua própria máquina física faz o papel das EC2s, por isso precisamos rodar o Backend e o Worker nos terminais.

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
