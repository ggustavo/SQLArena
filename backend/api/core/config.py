import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate .env in backend directory
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    PROJECT_NAME: str = "SQLArena API"
    SECRET_KEY: str = "supersecretkey-stateless-jwt-min-32-chars-for-ecs-scaling"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # AWS & Ministack Settings
    AWS_ENDPOINT_URL: str = "http://localhost:4566"
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = "test"
    AWS_SECRET_ACCESS_KEY: str = "test"

    # AWS Resources
    S3_BUCKET_NAME: str = "sqlarena-scripts"
    SQS_QUEUE_NAME: str = "sqlarena-submissions-queue"
    DYNAMODB_TABLE_NAME: str = "sqlarena-submission-logs"

    # ElastiCache (Redis)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 16379
    REDIS_CACHE_TTL_SECONDS: int = 300

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

    @property
    def rds1_database_url(self) -> str:
        return f"postgresql://{self.RDS1_USER}:{self.RDS1_PASSWORD}@{self.RDS1_HOST}:{self.RDS1_PORT}/{self.RDS1_DB}"

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
