from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from api.models.question import QuestionStatus


class QuestionCatalogItem(BaseModel):
    id: int
    title: str
    timeout_seconds: int
    status: QuestionStatus

    class Config:
        from_attributes = True


class QuestionDetailStudent(BaseModel):
    """View returned to students: context & problem statement, explicitly hiding expected query."""
    id: int
    title: str
    context: str
    timeout_seconds: int
    status: QuestionStatus

    class Config:
        from_attributes = True


class QuestionDetailTeacher(BaseModel):
    """Complete view returned to professors."""
    id: int
    title: str
    context: str
    expected_query: str
    timeout_seconds: int
    status: QuestionStatus
    s3_ddl_key: Optional[str] = None
    s3_dml_key: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
