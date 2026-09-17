from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class QuestionStatus(str, Enum):
    CREATING_TABLES = "creating_tables"
    READY = "ready"
    ERROR = "error"


class Question(SQLModel, table=True):
    __tablename__ = "questions"

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(nullable=False, max_length=255)
    context: str = Field(nullable=False)
    expected_query: str = Field(nullable=False)
    timeout_seconds: int = Field(default=5, nullable=False)
    status: QuestionStatus = Field(default=QuestionStatus.CREATING_TABLES, nullable=False)
    s3_ddl_key: Optional[str] = Field(default=None, nullable=True)
    s3_dml_key: Optional[str] = Field(default=None, nullable=True)
    created_by: int = Field(foreign_key="users.id", nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
