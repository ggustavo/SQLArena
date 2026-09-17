from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import SQLModel, Field


class Role(str, Enum):
    TEACHER = "teacher"
    STUDENT = "student"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False, max_length=255)
    hashed_password: str = Field(nullable=False)
    role: Role = Field(default=Role.STUDENT, nullable=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
