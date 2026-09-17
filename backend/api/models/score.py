from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class StudentScore(SQLModel, table=True):
    __tablename__ = "student_scores"

    id: Optional[int] = Field(default=None, primary_key=True)
    student_id: int = Field(foreign_key="users.id", index=True, nullable=False)
    question_id: int = Field(foreign_key="questions.id", index=True, nullable=False)
    best_score: float = Field(default=0.0, nullable=False)
    updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
