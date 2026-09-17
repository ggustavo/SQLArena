import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


class WorkerSettings(BaseSettings):
    # AWS Settings
    AWS_ENDPOINT_URL: str = "http://localhost:4566"
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"

    # Queue & Logs
    SQS_QUEUE_NAME: str = "sqlarena-submissions-queue"
    DYNAMODB_TABLE_NAME: str = "sqlarena-submission-logs"

    # RDS 1 (Metadata)
    RDS1_HOST: str = "localhost"
    RDS1_PORT: int = 15432
    RDS1_USER: str = "postgres"
    RDS1_PASSWORD: str = "postgrespassword"
    RDS1_DB: str = "app_db"

    # RDS 2 (Execution)
    RDS2_HOST: str = "localhost"
    RDS2_PORT: int = 15432
    RDS2_USER: str = "postgres"
    RDS2_PASSWORD: str = "postgrespassword"
    RDS2_DB: str = "app_db"
    RDS2_READONLY_USER: str = "postgres"
    RDS2_READONLY_PASSWORD: str = "postgrespassword"

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


worker_settings = WorkerSettings()
