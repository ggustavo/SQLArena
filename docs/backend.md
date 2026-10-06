# Backend SQLArena (FastAPI + AWS)

## 1. Visão Geral

O backend do SQLArena está inteiramente contido no diretório `app/`. Ele é construído em **FastAPI** e modularizado por responsabilidades de infraestrutura e serviços AWS.

### Estrutura de Diretórios e Módulos

```text
app/
├── api/                  # Camada HTTP REST (Rotas e Endpoints da API)
│   ├── auth.py           # Login de alunos/instrutores e emissão de JWT
│   ├── questions.py      # CRUD, listagem filtrada e publicação de questões
│   ├── submissions.py    # Submissão de SQL, polling de status e histórico
│   ├── categories.py     # Consulta de categorias pré-definidas
│   ├── audit.py          # Log de auditoria imutável (Requisito 5)
│   └── deps.py           # Injeção de dependências FastAPI (autenticação, DB)
├── auth/                 # Criptografia e Segurança
│   └── security.py       # Hash de senhas (bcrypt) e codificação de tokens (JWT)
├── cache/                # Cache em Memória e Controle de Taxa
│   └── redis_client.py   # Cliente Redis (ElastiCache) para cache de gabarito e rate limit (5s)
├── database/             # Camada Relacional (PostgreSQL 16 / Amazon RDS)
│   ├── models.py         # Modelos declarativos SQLAlchemy (User, Question, Category)
│   ├── session.py        # Engine e fábrica de sessões SessionLocal
│   ├── validator.py      # QuestionValidator: cria schemas isolados, roda DDL/DML e hash SHA-256
│   ├── seed.py           # Carga inicial determinística e validação das 21 questões
│   └── initial_data.json # Dataset canônico dos exercícios
├── dynamodb/             # Amazon DynamoDB
│   └── dynamo_manager.py # Tabelas de log imutável de submissões e ações de CRUD
├── s3/                   # Amazon S3
│   └── s3_manager.py     # Upload e download de schema.sql, data.sql e answer.sql
├── sqs/                  # Amazon SQS
│   └── queue_manager.py  # Fila de submissões desacoplada e Dead Letter Queue (DLQ)
├── worker/               # Processamento Assíncrono Desacoplado
│   ├── main.py           # Loop consumidor contínuo de mensagens da fila SQS
│   └── executor.py       # SandboxExecutor: execução restrita e segura de consultas de alunos
├── config.py             # Configurações centralizadas via Pydantic Settings e .env
└── main.py               # Ponto de entrada da aplicação FastAPI
```

---

## 2. Como Rodar a API

```bash
# Ativar o ambiente virtual
.\app\.venv\Scripts\Activate.ps1

# Iniciar o servidor de desenvolvimento
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Teste de saúde:
```bash
curl http://localhost:8000/health
# -> {"status":"healthy","service":"sqlarena-web-api","environment":"local"}
```

---

## 3. Como Rodar o Worker em Segundo Plano

```bash
python app/worker/main.py
```
O worker roda em loop contínuo consumindo mensagens da fila Amazon SQS (`sqlarena-submissions-queue`), executando as consultas no PostgreSQL isolado e persistindo os resultados no Redis e DynamoDB.
