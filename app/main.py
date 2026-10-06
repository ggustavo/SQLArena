import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.session import engine, Base
from app.s3.s3_manager import S3Manager
from app.dynamodb.dynamo_manager import DynamoDBManager
from app.sqs.queue_manager import SQSQueueManager
from app.cache.redis_client import redis_client

# Import routers
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.questions import router as questions_router
from app.api.submissions import router as submissions_router
from app.api.audit import router as audit_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("SQLArenaApp")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando SQLArena Backend...")
    # 1. Verifica/cria tabelas do RDS PostgreSQL
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("[✓] Banco RDS PostgreSQL conectado com sucesso.")
    except Exception as e:
        logger.error(f"[!] Erro ao conectar no RDS PostgreSQL: {e}")

    # 2. Verifica bucket S3
    try:
        s3 = S3Manager()
        s3.ensure_bucket_exists()
        logger.info(f"[✓] Bucket S3 '{s3.bucket_name}' pronto.")
    except Exception as e:
        logger.warning(f"[!] Aviso S3: {e}")

    # 3. Verifica tabelas DynamoDB
    try:
        dyn = DynamoDBManager()
        dyn.ensure_tables_exist()
        logger.info("[✓] Tabelas DynamoDB prontas.")
    except Exception as e:
        logger.warning(f"[!] Aviso DynamoDB: {e}")

    # 4. Verifica filas SQS
    try:
        sqs = SQSQueueManager()
        sqs.ensure_queues_exist()
        logger.info(f"[✓] Fila SQS '{sqs.queue_name}' pronta.")
    except Exception as e:
        logger.warning(f"[!] Aviso SQS: {e}")

    # 5. Verifica Redis
    if redis_client.ping():
        logger.info("[✓] Cache Redis conectado e operante.")
    else:
        logger.warning("[!] Não foi possível conectar ao Redis.")

    yield
    logger.info("Encerrando SQLArena Backend.")

app = FastAPI(
    title="SQLArena API",
    description="API RESTful de backend do SQLArena - Ensino e Avaliação Automatizada de SQL",
    version="1.0.0",
    lifespan=lifespan
)

# Configuração de CORS para permitir requisições do Frontend SPA
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoint de Health Check para o Application Load Balancer (ALB)
@app.get("/health", tags=["Health"])
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "sqlarena-web-api",
        "environment": settings.ENVIRONMENT
    }

# Registro dos Roteadores da API
app.include_router(auth_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(questions_router, prefix="/api")
app.include_router(submissions_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
