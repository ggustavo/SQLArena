import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_file = Path(__file__).resolve().parent / ".env"

class Settings(BaseSettings):
    ENVIRONMENT: str = "local"
    APP_PORT: int = 8000
    SECRET_KEY: str = "supersecretkey-local-dev-min-32-chars-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 dias

    # PostgreSQL RDS
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgrespassword@localhost:15432/app_db"
    RDS_HOST: str = "localhost"
    RDS_PORT: int = 15432
    RDS_USER: str = "postgres"
    RDS_PASSWORD: str = "postgrespassword"
    RDS_DB_NAME: str = "app_db"

    # Redis ElastiCache
    REDIS_URL: str = "redis://localhost:16379/0"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 16379

    # AWS / Ministack
    AWS_ENDPOINT_URL: Optional[str] = "http://localhost:4566"
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"

    # SQS
    SQS_QUEUE_NAME: str = "sqlarena-submissions-queue"
    SQS_DLQ_NAME: str = "sqlarena-submissions-queue-dlq"

    # S3 & DynamoDB
    S3_BUCKET_NAME: str = "sqlarena-questions-bucket"
    DYNAMO_SUBMISSIONS_TABLE: str = "sqlarena-submissions-log"
    DYNAMO_CRUD_TABLE: str = "sqlarena-crud-actions-log"

    model_config = SettingsConfigDict(
        env_file=str(_env_file) if _env_file.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
