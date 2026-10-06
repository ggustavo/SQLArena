# ⚔️ SQLArena - Plataforma de Ensino e Avaliação de SQL

Plataforma interativa para ensino e prática de consultas SQL em ambiente real **PostgreSQL 16** com isolamento por schemas (Sandbox), avaliação assíncrona via **Amazon SQS** e cache **Redis**.

---

## 🚀 Como Rodar o Projeto (Guia Rápido)

Siga os 5 passos abaixo para subir a aplicação completa do zero.

---

### Passo 1: Subir o Docker (Banco, Redis e Emulador AWS)
> ⚠️ **Importante:** Certifique-se de que o **Docker Desktop** está aberto e rodando antes de executar este comando.

Abra o terminal na **raiz do projeto** (`SQLArena/`):
```powershell
docker compose -f ministack/docker-compose.yml up -d
```
*Isso inicia 4 containers:*
* **PostgreSQL 16:** `localhost:15432` (Banco da aplicação e Sandbox)
* **Redis 7:** `localhost:16379` (Rate limit e Hashes dos gabaritos)
* **Ministack (AWS):** `http://localhost:4566` (S3, SQS e DynamoDB locais)
* **StackPort:** `http://localhost:8080` (Painel visual dos recursos AWS)

---

### Passo 2: Ativar o Python e Rodar o Seed
Na raiz do projeto (`SQLArena/`), execute no PowerShell:

```powershell
# 1. Ativar o ambiente virtual:
& app/.venv/Scripts/Activate.ps1

# (Caso o PowerShell bloqueie scripts, execute antes:)
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned

# 2. Instalar dependências (caso não tenha instalado):
pip install -r app/requirements.txt

# 3. Popular o banco com as 21 questões, scripts no S3 e hashes no Redis:
$env:PYTHONPATH="."
python app/database/seed.py
```
> ✅ Ao terminar, o script confirmará que as 12 categorias, usuários e 21 questões foram criados com sucesso.

---

### Passo 3: Ligar o Backend (FastAPI) — Terminal 1
Na raiz do projeto (`SQLArena/`), abra um terminal dedicado:

```powershell
# Ativar o ambiente virtual:
& app/.venv/Scripts/Activate.ps1

# Iniciar o servidor FastAPI:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

* 🌐 **API Rodando em:** [http://localhost:8000](http://localhost:8000)
* 📖 **Documentação Interativa (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
* 🩺 **Health Check:** [http://localhost:8000/api/health](http://localhost:8000/api/health)

---

### Passo 4: Ligar o Worker SQS (Motor Sandbox) — Terminal 2
Abra um **segundo terminal** na raiz do projeto (`SQLArena/`):

```powershell
# Ativar o ambiente virtual:
& app/.venv/Scripts/Activate.ps1

# Iniciar o Worker:
$env:PYTHONPATH="."
python app/worker/main.py
```

* ⚙️ **O que ele faz:** Fica escutando a fila SQS `sqlarena-submissions-queue`. Quando você clica em *"Executar"* no frontend, o worker pega a query, roda no schema isolado do PostgreSQL, compara o resultado via SHA-256 no Redis e atualiza o XP do aluno. Deixe esse terminal aberto!

---

### Passo 5: Ligar o Frontend (React + Vite) — Terminal 3
Abra um **terceiro terminal**, acesse a pasta `frontend`:

```powershell
# Entrar na pasta do frontend:
cd frontend

# Instalar dependências (apenas na primeira vez):
npm install

# Iniciar o servidor de desenvolvimento:
npm run dev
```

* 🚀 **Acesse o sistema no seu navegador:** **[http://localhost:5173](http://localhost:5173)**

---

## 🔑 Credenciais para Login

O seed já deixa criadas duas contas prontas:

| Perfil | Email | Senha | Funcionalidades |
| :--- | :--- | :--- | :--- |
| **Aluno** | `aluno@sqlarena.com` | `123456` | Mural de Questões, Arena de Código (Monaco Editor com `Ctrl+Enter`), Histórico em Modal, Pontuação de XP |
| **Instrutor** | `instrutor@sqlarena.com` | `123456` | Painel de Criação de Questões, validação de `ORDER BY`, categorias N:N, Logs de Auditoria |

---

## 🛑 Como Desligar e Limpar Tudo (Teardown)

Quando terminar de testar ou quiser resetar o ambiente:

1. **Parar as aplicações:** Pressione `Ctrl + C` nos terminais do Frontend, Worker e Backend.
2. **Destruir os containers e volumes Docker:**
   ```powershell
   docker compose -f ministack/docker-compose.yml down -v
   ```
   > A flag `-v` apaga os volumes do banco e cache, deixando a máquina 100% limpa.

---

## 🧪 Como Rodar os Testes Automatizados

Com a infraestrutura Docker ativa (Passo 1):

```powershell
# Na raiz do projeto, com o .venv ativo:
$env:PYTHONPATH="."
pytest app/testes/test_api.py app/testes/test_worker_e2e.py app/testes/test_e2e_full.py -v
```

Testes individuais dos módulos AWS locais:
```powershell
python app/testes/main_s3.py
python app/testes/main_sqs.py
python app/testes/main_dynamodb.py
```

---

## 🏛️ Arquitetura e Fluxo de Dados

```text
[ Aluno no Frontend (React :5173) ]
                 │
                 ▼ (HTTP / JWT)
     [ FastAPI Web API (:8000) ]
        │              │
        │ Rate Limit   │ Publica na fila
        ▼ (5s)         ▼
  [ Redis (:16379) ]  [ Amazon SQS (:4566) ]
                       │
                       ▼ Consome mensagem
              [ Worker Sandbox ]
                       │
     ┌─────────────────┼─────────────────┐
     │                 │                 │
     ▼                 ▼                 ▼
[ Postgres Sandbox ] [ Redis Hash ]    [ RDS PostgreSQL ]
  (Executa em          (Compara          (Concede +10 XP
   Schema Isolado       SHA-256 O(1))     se inédito)
   Read-Only 3s)       │
                       ▼
             [ Amazon DynamoDB ]
              (Log Imutável)
```

### Principais Componentes:
* **Frontend SPA (`frontend/`):** React 19 + Tailwind CSS v4 + Monaco Editor com atalho `Ctrl+Enter`, histórico em modal dinâmico e diagrama de banco.
* **FastAPI (`app/`):** Endpoints REST para autenticação JWT, categorias N:N, questões e submissões com rate limit.
* **Amazon SQS:** Fila assíncrona que absorve picos e desacopla a API dos Workers.
* **Worker Sandbox (`app/worker/`):** Executa queries em schemas isolados (`pergunta_X`), em modo estrito de leitura (`SELECT` only) e com timeout de 3 segundos.
* **Amazon S3:** Armazena os scripts SQL puros de cada questão (`schema.sql`, `data.sql`, `answer.sql`). Sem CSVs externos.
* **Redis:** Cache de rate limit por aluno (5 segundos) e hash SHA-256 canônico do gabarito para validação ultra-rápida em O(1).
* **DynamoDB:** Histórico completo de submissões e logs de auditoria de ações de instrutores.

---

## 🗺️ Estrutura de Pastas

```text
SQLArena/
├── ministack/                   # Docker Compose (PostgreSQL, Redis, Ministack, StackPort)
├── app/                         # Backend FastAPI, Workers e Banco
│   ├── main.py                  # Ponto de entrada FastAPI (porta 8000)
│   ├── backend/                 # Rotas da API (auth, questions, submissions, categories...)
│   ├── database/                # Modelos SQLAlchemy, conexão e script de seed
│   ├── worker/                  # Worker SQS e Sandbox PostgreSQL
│   ├── s3/                      # Gerenciador do Amazon S3
│   ├── sqs/                     # Gerenciador do Amazon SQS
│   ├── dynamodb/                # Gerenciador do Amazon DynamoDB
│   └── testes/                  # Suíte de testes automatizados com pytest
├── frontend/                    # Single Page Application React (porta 5173)
│   ├── src/pages/               # LoginPage, QuestionDashboard, ArenaPage, ProfessorPage...
│   ├── src/components/          # SqlEditor (Monaco), RelationalDiagram, Navbar...
│   └── src/services/            # Chamadas HTTP Axios para o backend (USE_MOCK = false)
└── terraform/                   # Infraestrutura como Código (IaC para deploy na AWS)
```

---

## ☁️ Deploy na Nuvem AWS (Terraform)

Para subir a infraestrutura real na sua conta da Amazon:

```powershell
cd terraform
terraform init
terraform plan -var-file="envs/aws.tfvars"
terraform apply -var-file="envs/aws.tfvars"
```
