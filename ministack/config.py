import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file located in the ministack folder
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# AWS Settings
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "test")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# RDS Settings
RDS_DB_NAME = os.getenv("RDS_DB_NAME", "app_db")
RDS_USERNAME = os.getenv("RDS_USERNAME", "postgres")
RDS_PASSWORD = os.getenv("RDS_PASSWORD", "postgrespassword")
