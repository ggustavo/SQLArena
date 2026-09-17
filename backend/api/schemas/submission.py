from datetime import datetime
from pydantic import BaseModel, Field


class SubmissionCreate(BaseModel):
    query: str = Field(..., min_length=1, description="Student's SQL answer")


class SubmissionAcceptedResponse(BaseModel):
    submission_id: str
    status: str = "accepted"
    message: str = "Query queued for asynchronous evaluation."


class StudentScoreRead(BaseModel):
    question_id: int
    best_score: float
    updated_at: datetime

    class Config:
        from_attributes = True
