# SQLArena - Backend API and Standalone Worker

Educational SQL grading and database learning system built with **FastAPI**, **SQLModel**, **PostgreSQL** (RDS 1 and RDS 2), **ElastiCache (Redis)**, **S3**, **SQS**, and **DynamoDB**.

Designed strictly following **SOLID principles** and enterprise cloud patterns.

---

## Architecture and Single Responsibility Structure

```
backend/
├── api/                           # FastAPI REST API Service
│   ├── core/
│   │   ├── config.py              # Environment configuration via Pydantic BaseSettings
│   │   ├── database.py            # RDS 1 connection pool and session dependency
│   │   ├── security.py            # Pure stateless JWT and bcrypt hashing
│   │   └── cache.py               # ElastiCache (Redis) Cache-Aside operations
│   ├── models/                    # SQLModel Database Tables
│   │   ├── user.py                # User entity and Role enum
│   │   ├── question.py            # Question entity and QuestionStatus enum
│   │   ├── score.py               # StudentScore entity
│   │   └── __init__.py            # Domain models export
│   ├── schemas/                   # Pydantic DTOs (Request / Response validation)
│   │   ├── auth.py                # Login, Registration, Token schemas
│   │   ├── question.py            # Question catalog and context schemas
│   │   └── submission.py          # Submission request/response schemas
│   ├── services/                  # Business Logic and External Integrations
│   │   ├── aws_client.py          # Boto3 client/resource factory (Ministack/AWS)
│   │   ├── storage_service.py     # S3 .sql script upload and download
│   │   ├── queue_service.py       # SQS message publishing
│   │   └── question_provisioner.py # BackgroundTask provisioning RDS 2 schemas and DDL/DML
│   ├── routes/                    # API Endpoints
│   │   ├── auth.py                # /auth/register, /auth/login
│   │   ├── questions.py           # /questions (Teacher create, Student catalog/context)
│   │   ├── submissions.py         # /questions/{id}/submit (Student SQS queueing)
│   │   ├── scores.py              # /scores/me (Student scores history)
│   │   └── __init__.py            # Route aggregator
│   ├── deps.py                    # Dependency injection (current_user, require_teacher, require_student)
│   └── main.py                    # FastAPI app wireup, lifespan, and CORS
│
├── worker/                        # Standalone Asynchronous Evaluation Worker
│   ├── config.py                  # Worker configuration settings
│   ├── db.py                      # Database connections for RDS 1 (Metadata) and RDS 2 (Read-Only)
│   ├── executor.py                # RDS 2 safe execution (READ ONLY, statement_timeout, search_path)
│   ├── validator.py               # Similarity metric (0-100%) and mandatory ORDER BY rule
│   ├── ddb_logger.py              # DynamoDB immutable execution logging
│   ├── score_service.py           # RDS 1 score updating (best score consolidation)
│   ├── consumer.py                # SQS consumer loop and workflow orchestration
│   └── main.py                    # Worker CLI entrypoint with graceful shutdown
│
├── samples/                       # Sample test scripts
│   ├── ddl_sample.sql             # Sample table definitions
│   └── dml_sample.sql             # Sample data seeds
│
├── .env                           # Unified environment variables
├── requirements.txt               # Dependencies
└── README.md                      # Documentation
```

---

## How to Run

### 1. Setup Virtual Environment
```bash
cd backend

# On Linux / macOS:
python3 -m venv .venv
source .venv/bin/activate

# On Windows:
python -m venv .venv
.venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Run the FastAPI Server
From the `backend` folder:
```bash
uvicorn api.main:app --reload --port 8000
```
- Interactive Swagger Docs: `http://localhost:8000/docs`
- Healthcheck: `http://localhost:8000/health`

### 3. Run the Standalone Worker (Separate Terminal)
From the `backend` folder:
```bash
# On Linux / macOS:
source .venv/bin/activate

# On Windows:
.venv\Scripts\activate

python -m worker.main
```

---

## SOLID Principles in Action

1. **Single Responsibility Principle (SRP):**
   - `storage_service.py` only handles S3 storage operations.
   - `queue_service.py` only handles SQS message publishing.
   - `question_provisioner.py` only handles RDS 2 schema setup and data seeding.
   - `executor.py` only handles safe query execution in RDS 2.
   - `validator.py` only handles comparing result sets and calculating similarity scores.
   - `ddb_logger.py` only handles persisting immutable execution attempts to DynamoDB.
   - `score_service.py` only handles score consolidation in RDS 1.
2. **Open/Closed Principle (OCP):**
   - The validation strategy in `validator.py` can be extended with new grading criteria without modifying the executor or consumer.
3. **Dependency Inversion Principle (DIP):**
   - Routes and workers depend on abstractions and factories (`DatabaseConnectionFactory`, `CacheService`, `get_session`) rather than hardcoded connections.
