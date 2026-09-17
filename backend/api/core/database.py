from typing import Generator
from sqlmodel import Session, SQLModel, create_engine
from api.core.config import settings

# Connection pool for RDS 1 (PostgreSQL Metadata Database)
engine = create_engine(
    settings.rds1_database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)


def init_db() -> None:
    """Initializes metadata tables in RDS 1."""
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding database sessions."""
    with Session(engine) as session:
        yield session
