# SQLArena - Plataforma de Ensino e Avaliação de SQL

O **SQLArena** é uma plataforma distribuída, elástica e interativa para o ensino e prática de consultas SQL. Ela permite que instrutores cadastrem exercícios práticos e que alunos resolvam desafios com execução real em um banco de dados **PostgreSQL 16** isolado por schema, recebendo feedback instantâneo sobre acerto e desempenho.

A arquitetura do sistema adota o padrão de **Single Page Application (SPA)** no frontend comunicando-se assincronamente com uma **API FastAPI**, orquestrada por mensageria com **Amazon SQS**, armazenamento de scripts no **Amazon S3**, cache e rate limit no **Redis**, persistência relacional no **AWS RDS PostgreSQL**, logs imutáveis no **Amazon DynamoDB** e **Workers em background** com motor de execução isolado (Sandbox).

---

## 1. Arquitetura da Solução

```text
[ Aluno / Frontend React (Vite :5173) ]
                     │
                     ▼ (HTTP / JWT)
         [ FastAPI Web API (:8000) ]
            │              │
            │ (Rate Limit) │ (Publica Submissão)
            ▼              ▼
     [ Redis (:16379) ]  [ Amazon SQS (:4566) ]
                           │
                           ▼ (Consome mensagem)
                  [ Worker de Avaliação ]
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
[ PostgreSQL Sandbox ]   [ Redis Hash ]    [ RDS Metadata ]
  (Executa em Schema      (Compara SHA-256    (Concede +10 XP
   Isolado Read-Only)     com Gabarito O(1))  para inédito)
                           │
                           ▼
                 [ Amazon DynamoDB ]
                  (Log Imutável)
```

### Componentes Principais:
1. **Frontend SPA (`frontend/`):** React 19 + Tailwind CSS v4 + Monaco Editor, com atalhos de execução (`Ctrl + Enter`), histórico persistente em modal sem perda de contexto e visualização de schema relacional.
2. **FastAPI Web API (`app/main.py` e `app/backend/`):** Autenticação JWT, CRUD de categorias N:N e questões, validação de rate limit (5s) e despacho assíncrono para a fila SQS.
3. **Fila Amazon SQS (`sqlarena-submissions-queue`):** Desacopla a camada web do processamento pesado.
4. **Worker Sandbox (`app/worker/`):** Consome a fila, executa as consultas no PostgreSQL dentro de schemas isolados (`pergunta_X`), em modo *Read-Only* e com `statement_timeout = 3000ms`.
5. **Amazon S3 (`sqlarena-questions-bucket`):** Armazena os scripts SQL puros de cada questão (`schema.sql`, `data.sql`, `answer.sql`). Sem dependência de CSVs ou binários externos.
6. **Redis / ElastiCache:** Rate limit global por aluno (5s) e cache do Hash SHA-256 do gabarito canônico para validação instantânea em O(1).
7. **PostgreSQL / RDS:** Banco relacional para usuários, categorias N:N, questões e pontuações consolidadas.
8. **Amazon DynamoDB:** Log imutável de submissões (`sqlarena-submissions-log`) e auditoria de ações (`sqlarena-crud-actions-log`).
9. **Infraestrutura como Código (`terraform/`):** VPC, Subnets, Duplo Auto Scaling Group (ASG 1 para API e ASG 2 para Workers), ALB, RDS, ElastiCache, SQS, S3 e DynamoDB.

---

## 2. Pré-requisitos do Sistema

* **Docker Desktop** (em execução) com suporte a Docker Compose.
* **Python 3.11+** ou **3.12+** instalado.
* **Node.js 18+** e **npm** instalados.
* **Terraform CLI 1.5+** (opcional, para validação da infraestrutura IaC e deploy na nuvem).

---

## 3. Passo a Passo Completo: Executar a Aplicação Localmente

Siga os passos abaixo no **PowerShell** a partir da raiz do repositório (`C:\Users\Gustavo\Desktop\SQLArena`).

### Passo 1: Subir a Infraestrutura Emulada (Docker)
Inicie os serviços do banco relacional PostgreSQL, cache Redis, emulador de serviços AWS (Ministack) e o painel StackPort:

```powershell
docker compose -f ministack/docker-compose.yml up -d
```

Verifique se todos os containers estão ativos:
```powershell
docker ps
```
> Deverão estar rodando 4 containers: `sqlarena-postgres`, `sqlarena-redis`, `ministack` e `stackport`.

---

### Passo 2: Ativar o Ambiente Virtual Python e Instalar Dependências
Se ainda não possuir o `.venv`, crie e ative:

```powershell
# Criar o ambiente virtual (caso não exista):
python -m venv app/.venv

# Permitir execução de scripts no PowerShell (se necessário):
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# Ativar o ambiente virtual:
& app/.venv/Scripts/Activate.ps1

# Instalar dependências:
pip install -r app/requirements.txt
```

---

### Passo 3: Executar o Seed Inicial de Dados
O script de seed cria as tabelas no PostgreSQL (RDS), cadastra as 12 categorias, usuários de teste, 21 questões reais com scripts no S3, inicializa os schemas de sandbox no PostgreSQL, computa os hashes SHA-256 dos gabaritos no Redis e provisiona tabelas no DynamoDB e fila no SQS:

```powershell
$env:PYTHONPATH="."
& app/.venv/Scripts/python.exe app/database/seed.py
```

---

### Passo 4: Iniciar o Backend FastAPI (Terminal 1)
Em um terminal dedicado com o `.venv` ativo:

```powershell
# Na raiz do projeto:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
> A API estará disponível em:
> * Documentação Interativa (Swagger): **[http://localhost:8000/docs](http://localhost:8000/docs)**
> * Endpoint de Saúde: **[http://localhost:8000/api/health](http://localhost:8000/api/health)**

---

### Passo 5: Iniciar o Worker SQS (Terminal 2)
Abra um **segundo terminal**, ative o `.venv` e inicie o Worker de processamento assíncrono:

```powershell
& app/.venv/Scripts/Activate.ps1
$env:PYTHONPATH="."
python app/worker/main.py
```
> O Worker ficará em loop consumindo mensagens da fila `sqlarena-submissions-queue`. Conforme os alunos enviarem códigos na Arena, os logs de validação, hash e atribuição de XP aparecerão aqui em tempo real.

---

### Passo 6: Iniciar o Frontend React (Terminal 3)
Abra um **terceiro terminal**, acesse a pasta `frontend` e inicie o servidor Vite:

```powershell
cd frontend
npm run dev
```
> A aplicação web estará acessível em: **[http://localhost:5173](http://localhost:5173)**

---

## 4. Credenciais de Acesso & Contas de Teste

O seed provisiona automaticamente duas contas prontas para uso:

| Perfil | Email | Senha | Funcionalidades |
| :--- | :--- | :--- | :--- |
| **Aluno** | `aluno@sqlarena.com` | `123456` | Visualizar Dashboard, resolver questões na Arena, rodar com `Ctrl+Enter`, ver histórico e pontuar XP |
| **Instrutor** | `instrutor@sqlarena.com` | `123456` | Painel de criação de questões, validação de `ORDER BY`, categorias N:N e auditoria |

---

## 5. Dashboards e Portas do Sistema

| Serviço | Endereço Local | Descrição |
| :--- | :--- | :--- |
| **Frontend SPA** | `http://localhost:5173` | Interface React + Tailwind CSS v4 |
| **Backend API Docs** | `http://localhost:8000/docs` | Documentação Swagger interativa do FastAPI |
| **StackPort GUI** | `http://localhost:8080` | Interface visual para navegar nos buckets S3 e filas SQS |
| **PostgreSQL RDS** | `localhost:15432` | Banco relacional central (`app_db` / user `postgres`) |
| **Redis Cache** | `localhost:16379` | Cache de rate limit e hashes SHA-256 |
| **Ministack AWS Gateway** | `http://localhost:4566` | Emulador das APIs S3, SQS e DynamoDB |

---

## 6. Execução da Suíte de Testes Automatizados

O projeto inclui testes de unidade e ponta a ponta (E2E) cobrindo API, SQS, Worker e banco:

```powershell
# Com o .venv ativo e a infraestrutura Docker rodando:
$env:PYTHONPATH="."
pytest app/testes/test_api.py app/testes/test_worker_e2e.py app/testes/test_e2e_full.py -v
```

Para rodar os testes individuais dos módulos de serviço AWS:
```powershell
python app/testes/main_s3.py
python app/testes/main_sqs.py
python app/testes/main_dynamodb.py
```

---

## 7. Como Desligar e Destruir o Ambiente (Teardown)

Quando desejar encerrar a execução e resetar todo o ambiente de desenvolvimento:

1. **Parar os servidores em execução nos terminais:**
   Pressione `Ctrl + C` nos terminais do FastAPI, do Worker e do Frontend.

2. **Destruir os containers Docker e remover os volumes de dados:**
   ```powershell
   docker compose -f ministack/docker-compose.yml down -v
   ```
   > A flag `-v` remove os volumes associados, garantindo que nenhum resíduo de banco ou cache permaneça armazenado.

---

## 8. Estrutura de Diretórios

```text
SQLArena/
├── ministack/                   # Configuração e persistência do emulador local
│   ├── docker-compose.yml       # Orquestração do Postgres, Redis, Ministack e StackPort
│   └── data/                    # Dados locais persistidos
│
├── terraform/                   # Infraestrutura como Código (IaC)
│   ├── providers.tf             # Configuração do provedor AWS
│   ├── vpc.tf                   # Rede, subnets públicas/privadas e gateways
│   ├── alb.tf                   # Application Load Balancer
│   ├── asg.tf                   # Auto Scaling Group da Camada Web (API)
│   ├── worker_asg.tf            # Auto Scaling Group da Camada de Workers
│   ├── rds.tf                   # Instância PostgreSQL RDS
│   ├── elasticache.tf           # Cluster Redis ElastiCache
│   ├── s3.tf                    # Bucket para scripts das questões
│   ├── sqs.tf                   # Fila principal de submissões e Dead Letter Queue (DLQ)
│   ├── dynamodb.tf              # Tabelas de histórico e auditoria
│   └── envs/                    # Variáveis para local (local.tfvars) e AWS (aws.tfvars)
│
├── app/                         # Backend, Microsserviços e Banco
│   ├── main.py                  # Ponto de entrada unificado da aplicação FastAPI
│   ├── redis_client.py          # Cliente gerenciador do Redis (hashes e rate limit)
│   ├── backend/                 # API FastAPI com routers modularizados
│   │   ├── main.py              # Exporta a aplicação web
│   │   └── routers/             # Endpoints (auth, questions, submissions, categories, audit)
│   ├── database/                # Conexão SQLAlchemy, modelos relacionais e seed
│   │   ├── connection.py        # Pool de conexões RDS
│   │   ├── models.py            # Modelos (User, Question, Category, Submission)
│   │   ├── seed.py              # Script populador completo com 21 questões reais
│   │   └── initial_data.json    # Dados das 21 questões e scripts SQL
│   ├── worker/                  # Serviço Worker assíncrono
│   │   ├── main.py              # Inicializador do Worker de consumo da fila
│   │   └── worker_service.py    # Motor de execução segura em Sandbox PostgreSQL
│   ├── s3/                      # Gerenciador do Amazon S3 (upload/download scripts)
│   ├── sqs/                     # Gerenciador do Amazon SQS (envio, recepção e purge)
│   ├── dynamodb/                # Gerenciador do Amazon DynamoDB (logs imutáveis)
│   └── testes/                  # Suíte de testes unitários e de integração
│
└── frontend/                    # Single Page Application (React 19 + Vite 6 + Tailwind CSS v4)
    ├── src/
    │   ├── components/          # Componentes (Navbar, SqlEditor, RelationalDiagram, HistoryModal...)
    │   ├── pages/               # Páginas (LoginPage, QuestionDashboard, ArenaPage, ProfessorPage...)
    │   └── services/            # Camada de serviços HTTP conectada à API FastAPI
    └── package.json
```

---

## 9. Deploy na Nuvem AWS via Terraform

Para provisionar a infraestrutura completa na conta AWS real:

```powershell
cd terraform

# Inicializar os provedores:
terraform init

# Visualizar o plano de recursos que serão criados:
terraform plan -var-file="envs/aws.tfvars"

# Aplicar o provisionamento na AWS:
terraform apply -var-file="envs/aws.tfvars"
```

Para destruir os recursos na AWS ao concluir:
```powershell
terraform destroy -var-file="envs/aws.tfvars"
```
