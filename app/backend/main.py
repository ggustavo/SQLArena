"""
Ponto de entrada da API do SQLArena (compatibilidade com app.backend.main).
Expõe a aplicação FastAPI completa integrada com PostgreSQL (RDS),
Amazon S3, Amazon DynamoDB, Amazon SQS e Redis.

Permite rodar:
    uvicorn app.backend.main:app --reload --port 8000
ou:
    uvicorn app.main:app --reload --port 8000
"""
from app.main import app

__all__ = ["app"]
