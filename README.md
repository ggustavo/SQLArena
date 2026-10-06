# ⚔️ SQLArena - Plataforma de Ensino e Avaliação de SQL

Plataforma distribuída para prática e avaliação de consultas SQL em ambiente real **PostgreSQL 16** com isolamento por schemas (Sandbox), avaliação assíncrona desacoplada via **Amazon SQS**, cache de validação via **Redis** e Infraestrutura como Código via **Terraform**.

---

## 🏛️ Arquitetura do Sistema

```text
                                  ┌─────────────────────────────┐
                                  │      Usuário / Navegador    │
                                  └──────────────┬──────────────┘
                                                 │ HTTP (Porta 80)
                                                 ▼
                                  ┌─────────────────────────────┐
                                  │  Application Load Balancer  │
                                  └──────────────┬──────────────┘
                                                 │ Porta 8000
                                                 ▼
                     ┌───────────────────────────────────────────────────────┐
                     │            Camada Web (ASG - Instâncias EC2)          │
                     │  ┌─────────────────────────────────────────────────┐  │
                     │  │   FastAPI (Uvicorn)                             │  │
                     │  │   • SPA React (frontend/dist) servida no root   │  │
                     │  │   • API REST (/api/auth, /api/questions, etc.) │  │
                     │  └────────┬───────────────────────┬────────────────┘  │
                     └───────────┼───────────────────────┼───────────────────┘
                                 │                       │ Despacha Submissão
                Consulta / Login │                       ▼
                                 │             ┌───────────────────┐
                                 │             │     Amazon SQS    │
                                 │             │ (Fila Principal)  │
                                 │             └─────────┬─────────┘
                                 │                       │ Consome
                                 ▼                       ▼
┌──────────────────────────────────────────┐   ┌──────────────────────────────────────────┐
│             Bancos de Dados              │   │         Camada de Workers (ASG)          │
│ • Amazon RDS (PostgreSQL 16):            │   │  • Worker Python (app/worker/main.py)    │
│   - Metadados, Usuários, Questões        │◄──┤  • Execução em Sandbox (Schemas isolados)│
│ • Amazon ElastiCache (Redis):            │   │  • Comparação de Hash SHA-256            │
│   - Rate Limit e Cache de Hashes         │   └────────────────────┬─────────────────────┘
│ • Amazon S3:                             │                        │ Registra Execuções
│   - Scripts SQL de preparação e limpeza  │                        ▼
│ • Amazon DynamoDB:                       │           ┌────────────────────────┐
│   - Logs imutáveis de submissões e audit │           │     Amazon DynamoDB    │
└──────────────────────────────────────────┘           │ (Histórico e Auditoria)│
                                                       └────────────────────────┘
```

---

## 🧭 Visão dos Dois Ambientes: Local vs Nuvem AWS

O projeto foi desenhado para funcionar de forma idêntica em dois cenários:

| Recurso | 1. AMBIENTE LOCAL (Desenvolvimento no PC) | 2. NUVEM REAL (AWS Academy Learner Lab) |
| :--- | :--- | :--- |
| **Infraestrutura Base** | Docker Compose: Postgres 16 + Redis 7 + Ministack AWS | AWS Gerenciada (RDS Postgres, ElastiCache Redis, VPC, Subnets) |
| **Serviços AWS Emulados** | S3, SQS, DynamoDB no Ministack (Porta 4566) | S3, SQS + DLQ, DynamoDB nativos da AWS |
| **Terraform Workspace** | `envs/local.tfvars` | `envs/aws.tfvars` + `credentials.auto.tfvars` |
| **Camada Web** | Terminal 1 (`uvicorn`) + Terminal 3 (`npm run dev`) | Instâncias EC2 gerenciadas por Auto Scaling Group (Web ASG) |
| **Camada de Workers** | Terminal 2 (`python app/worker/main.py`) | Instâncias EC2 gerenciadas por Auto Scaling Group (Worker ASG) |
| **Ponto de Entrada** | Frontend em `http://localhost:5173` | DNS público do Application Load Balancer (`alb_dns_name`) |

---

## 📂 Estrutura e Organização do Projeto

```text
SQLArena/
├── app/
│   ├── api/            # Rotas REST (FastAPI): auth, questions, submissions, audit, etc.
│   ├── auth/           # Utilitários de autenticação, hashing de senhas e RBAC
│   ├── cache/          # Cliente Redis, controle de Rate Limit (5s) e hashes
│   ├── database/       # PostgreSQL: Engine SQLAlchemy, modelos, seed.py e validator.py
│   ├── dynamodb/       # Gerenciador de tabelas NoSQL de submissões e logs de auditoria
│   ├── s3/             # Gerenciador do bucket S3 para scripts DDL/DML das questões
│   ├── sqs/            # Produtor e consumidor de mensagens da fila Amazon SQS
│   ├── worker/         # Processador assíncrono de avaliações em schemas sandbox
│   ├── testes/         # Testes automatizados unitários e de integração E2E
│   └── main.py         # App FastAPI + Ponto de montagem da SPA React compilada
├── frontend/           # Aplicação React 18, Vite, Tailwind CSS e Monaco Editor
├── ministack/          # Compose local com Postgres, Redis e emulador AWS
└── terraform/          # Infraestrutura como Código para Ministack e AWS Academy
    ├── envs/
    │   ├── local.tfvars                # Variáveis do ambiente Docker/Ministack
    │   └── aws.tfvars                  # Configurações para a AWS Nuvem (Região, S3)
    └── credentials.auto.tfvars.example # Template de credenciais temporárias da AWS
```

---

# 💻 TRILHA 1: AMBIENTE LOCAL (Desenvolvimento no seu PC)

> [!IMPORTANT]
> ### ⚠️ Por que rodar o Backend e o Worker em terminais separados no seu PC?
> * **Na AWS Real (Nuvem):** O Terraform cria servidores virtuais **EC2 reais**. Quando as máquinas ligam, a AWS executa automaticamente o script `user_data`, que sobe a Camada Web e a Camada de Workers de forma autônoma.
> * **No seu PC (Ministack Local):** O Ministack emula APIs AWS, mas **não cria máquinas virtuais**. A sua máquina física faz o papel das EC2s:
>   * O **Terminal 1** (`uvicorn`) faz o papel da EC2 da Camada Web.
>   * O **Terminal 2** (`python app/worker/main.py`) faz o papel da EC2 dos Workers.
>   * O **Terminal 3** (`npm run dev`) roda o servidor de desenvolvimento do React.
> * **O que acontece se o Worker não estiver rodando?**
>   A consulta enviada pelo usuário cai na fila **Amazon SQS**. Se o **Worker não estiver rodando no Terminal 2**, **ninguém processa a fila**, e a submissão fica indefinidamente como *"Processando..."*.

---

### Passo 1: Subir a Infraestrutura Base (Docker)
No PowerShell na raiz do projeto (`SQLArena/`):
```powershell
docker compose -f ministack/docker-compose.yml up -d
```
*Inicia o PostgreSQL 16 (porta 15432), Redis 7 (porta 16379), Ministack AWS (porta 4566) e o painel StackPort (porta 8080).*

---

### Passo 2: Provisionar a Infraestrutura Local via Terraform (IaC)
```powershell
cd terraform
terraform init
terraform apply -var-file="envs/local.tfvars" -auto-approve
cd ..
```
*O Terraform criará no Ministack o Bucket S3, Fila SQS + DLQ, Tabelas DynamoDB, VPC e definições de banco.*

---

### Passo 3: Ativar o Python e Rodar o Seed
Na raiz do projeto (`SQLArena/`):
```powershell
# Ativar o ambiente virtual:
& app/.venv/Scripts/Activate.ps1

# (Caso o PowerShell restrinja scripts, execute uma vez:)
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# Instalar dependências (apenas na primeira vez):
pip install -r app/requirements.txt

# Executar o seed:
$env:PYTHONPATH="."
python app/database/seed.py
```
> ✅ O `seed.py` utiliza o `QuestionValidator` para validar as 21 questões em schemas isolados no PostgreSQL, extrair colunas reais, gerar os hashes canônicos SHA-256 no RDS e no Redis, enviar os scripts para o S3 e cadastrar os usuários de teste.

---

### Passo 4: Ligar o Backend FastAPI (Terminal 1)
Na raiz do projeto (`SQLArena/`):
```powershell
& app/.venv/Scripts/Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
* 🌐 **API Rodando em:** [http://localhost:8000](http://localhost:8000)
* 📖 **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* 🩺 **Health Check:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Passo 5: Ligar o Worker SQS (Terminal 2)
Abra um **segundo terminal** na raiz do projeto (`SQLArena/`):
```powershell
& app/.venv/Scripts/Activate.ps1
$env:PYTHONPATH="."
python app/worker/main.py
```
* ⚙️ **Função:** Fica em loop consumindo a fila SQS `sqlarena-submissions-queue`. Quando uma query chega, executa em schema isolado, compara o hash no Redis e registra no RDS e DynamoDB.

---

### Passo 6: Ligar o Frontend React (Terminal 3)
Abra um **terceiro terminal**, acesse a pasta `frontend`:
```powershell
cd frontend
npm install    # (apenas na primeira vez)
npm run dev
```
* 🚀 **Acesse no navegador:** **[http://localhost:5173](http://localhost:5173)**

---

### 🔑 Credenciais Prontas para Teste

| Perfil | Email | Senha | Acesso |
| :--- | :--- | :--- | :--- |
| **Aluno** | `aluno@sqlarena.com` | `123456` | Dashboard, Arena Monaco (editor com restauração da última tentativa), Histórico em Modal, Pontuação |
| **Instrutor** | `instrutor@sqlarena.com` | `123456` | Painel de Questões, Validação Dinâmica Sandbox, Categorias N:N, Auditoria de Ações |

---

### 🖥️ Resumo dos 3 Terminais Necessários Localmente

| Terminal | O que roda | Comando | O que faz no sistema |
| :---: | :--- | :--- | :--- |
| **Terminal 1** | **Backend API** | `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000` | Recebe requisições HTTP e envia submissões para o SQS |
| **Terminal 2** | **Worker SQS** | `python app/worker/main.py` | **OBRIGATÓRIO:** Consome a fila SQS e avalia as consultas SQL |
| **Terminal 3** | **Frontend SPA** | `cd frontend; npm run dev` | Interface web em React no navegador (`http://localhost:5173`) |

---

### ❓ Perguntas Frequentes & Diagnóstico (Troubleshooting)

#### 1. "Cliquei em 'Executar' na Arena e a tela ficou em 'Processando...' sem sair do lugar?"
* **Causa:** O **Worker (Terminal 2)** não está ligado! A consulta foi despachada para a fila SQS, mas ninguém está consumindo a fila.
* **Solução:** Abra o **Terminal 2** com o `.venv` ativo e execute:
  ```powershell
  & app/.venv/Scripts/Activate.ps1
  $env:PYTHONPATH="."
  python app/worker/main.py
  ```
  Assim que o Worker ligar, ele pegará as consultas pendentes imediatamente, executará no PostgreSQL Sandbox e a tela atualizará no mesmo instante!

#### 2. "O Terraform não deveria ligar as máquinas EC2 e o Worker sozinho?"
* **Na AWS Real:** SIM. O Terraform provisiona instâncias EC2 gerenciadas pela Amazon e executa o script `user_data`, que configura e sobe o sistema sozinho.
* **No Computador Local:** NÃO. O Ministack é apenas um emulador de API e não cria máquinas virtuais no Windows. No seu computador, a sua própria máquina física faz o papel das instâncias EC2.

---

### 🛑 Como Desligar / Destruir o Ambiente Local
1. Finalize com `Ctrl + C` os terminais do Frontend, Worker e Backend.
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

Quando você for testar ou apresentar o projeto na sua conta da **AWS Academy Learner Lab**:

### 1. Obter as Credenciais no AWS Academy
1. Entre no seu **AWS Academy Learner Lab** e clique no botão verde **Start Lab**.
2. Quando o status mudar para verde, clique no botão **AWS Details**.
3. Na seção **AWS CLI**, copie os valores das credenciais temporárias:
   * `aws_access_key_id`
   * `aws_secret_access_key`
   * `aws_session_token`

---

### 2. Configurar as Credenciais Seguras (Ignoradas pelo Git)
Para garantir que suas chaves temporárias **nunca sejam enviadas para o GitHub**, o repositório já inclui o arquivo `credentials.auto.tfvars` no `.gitignore`.

Na pasta `terraform/`, crie o arquivo `credentials.auto.tfvars` (você pode copiar o modelo [`credentials.auto.tfvars.example`](terraform/credentials.auto.tfvars.example)):

```hcl
aws_access_key    = "ASIA..."
aws_secret_key    = "..."
aws_session_token = "IQoJb3JpZ2luX2VjE..."
```

> [!TIP]
> **Por que o arquivo termina com `.auto.tfvars`?**
> Todo arquivo com sufixo `.auto.tfvars` é carregado **automaticamente** pelo Terraform em comandos como `plan`, `apply` e `destroy`, sem que você precise passar nenhum parâmetro de credencial na linha de comando. E graças ao `.gitignore`, suas chaves permanecem 100% seguras na sua máquina.

---

### 3. Ajustar o Nome Único do Bucket S3
Abra o arquivo [`terraform/envs/aws.tfvars`](terraform/envs/aws.tfvars) e defina um nome exclusivo para o bucket S3 (nomes de bucket S3 são únicos no mundo inteiro):

```hcl
aws_region     = "us-east-1"
s3_bucket_name = "sqlarena-questions-bucket-academy-gustavo"
```

---

### 4. Executar o Provisionamento no AWS Academy
No PowerShell dentro da pasta `terraform/`:

```powershell
cd terraform

# 1. Inicializar os provedores:
terraform init

# 2. Visualizar o plano de recursos:
terraform plan -var-file="envs/aws.tfvars"

# 3. Aplicar e provisionar a infraestrutura completa na nuvem:
terraform apply -var-file="envs/aws.tfvars"
```

---

### 5. O Que o Terraform Cria na AWS Real

* 🌐 **VPC Própria:** Rede isolada com subnets públicas e privadas distribuídas nas Availability Zones `us-east-1a` e `us-east-1b`, Internet Gateway e Route Tables.
* ⚖️ **Application Load Balancer (ALB):** Ponto de entrada público HTTP (Porta 80) balanceando tráfego entre instâncias da Camada Web.
* 📈 **Auto Scaling Group Web (Frontend + Backend):** Instâncias EC2 em subnet pública executando FastAPI e servindo o Frontend React compilado na porta 8000, com Target Tracking baseado em utilização de CPU.
* ⚡ **Auto Scaling Group Workers (Sandbox):** Instâncias EC2 dedicadas ao consumo da fila SQS, com políticas de escala baseadas na métrica `ApproximateNumberOfMessagesVisible` da fila SQS.
* 🗄️ **AWS RDS PostgreSQL 16:** Banco de dados relacional gerenciado em Subnet Group dedicada com isolamento por Security Group.
* 🏎️ **AWS ElastiCache Redis:** Cluster em memória gerenciado em Subnet Group própria para rate limiting (5s) e cache de hashes SHA-256.
* 🪣 **Amazon S3:** Bucket para armazenamento dos scripts DDL/DML de preparação e teardown de cada questão.
* 📬 **Amazon SQS + DLQ:** Fila de mensageria assíncrona desacoplada com Dead Letter Queue após 3 tentativas de falha.
* 📄 **Amazon DynamoDB:** Tabelas NoSQL em modo On-Demand para histórico de submissões e logs de auditoria.

---

### 6. Como a AWS Inicializa a Aplicação (Bootstrapping Automático)

Você **não precisa conectar via SSH** nas máquinas para subir nada manual. Os scripts `user_data` definidos no Terraform cuidam do ciclo de vida completo:

1. **Camada Web (EC2 Web):**
   * Clona o repositório oficial do projeto: `git clone https://github.com/Gustav0Carvalho/SQLArena.git`
   * Instala dependências de sistema (Python 3.11, Node.js 20, Git, PostgreSQL client)
   * Instala dependências do frontend e compila a SPA React (`npm install && npm run build`) gerando `frontend/dist/`
   * Configura as variáveis de ambiente com os endpoints reais do RDS, Redis, SQS, S3 e DynamoDB
   * Executa o `seed.py`, criando as tabelas, validando as 21 questões com `QuestionValidator` e populando os dados iniciais
   * Inicia o Uvicorn como serviço gerenciado pelo systemd (`sqlarena-web.service`)
   * O FastAPI serve a SPA React diretamente pelo endpoint raiz e a API REST em `/api/...`

2. **Camada de Workers (EC2 Worker):**
   * Clona o repositório
   * Instala as dependências Python
   * Inicia o daemon consumidor da fila SQS como serviço do systemd (`sqlarena-worker.service`)
   * O Worker consome as mensagens da fila SQS, valida a consulta em sandbox no RDS e registra os resultados no DynamoDB

> ⏳ **Tempo de inicialização (Bootstrapping):**
> O processo de download de pacotes, build do React e execução do seed leva aproximadamente **3 a 4 minutos** após o `terraform apply` concluir. Aguarde esse intervalo para acessar a aplicação.

---

### 7. Acessar a Aplicação na Nuvem

Após o término do `terraform apply`, visualize a URL pública do Load Balancer exibida nos outputs:

```text
Outputs:
alb_dns_name = "sqlarena-alb-xxxxxxxx.us-east-1.elb.amazonaws.com"
```

Abra seu navegador e acesse:
* 🚀 **Plataforma Web Completa:** `http://<alb_dns_name>`
* 📖 **Documentação Swagger (Swagger UI):** `http://<alb_dns_name>/docs`
* 🩺 **Health Check:** `http://<alb_dns_name>/api/health`

---

### 8. Monitoramento e Diagnóstico na Nuvem

Se precisar inspecionar o funcionamento dos serviços dentro das instâncias EC2:
* **Logs da Camada Web (FastAPI + SPA):**
  ```bash
  journalctl -u sqlarena-web.service -f
  ```
* **Logs da Camada de Workers:**
  ```bash
  journalctl -u sqlarena-worker.service -f
  ```
* **Logs de inicialização da máquina (User Data):**
  ```bash
  tail -f /var/log/cloud-init-output.log
  ```

---

### 9. Destruir os Recursos no AWS Academy (Liberar Créditos)

Quando finalizar os testes ou a apresentação, destrua todos os recursos da nuvem para não esgotar os créditos do seu Learner Lab:

```powershell
cd terraform
terraform destroy -var-file="envs/aws.tfvars"
```

---

## 🧪 Suíte de Testes Automatizados (pytest)

Com a infraestrutura ativa (localmente no Ministack ou na AWS):

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
