from typing import List
from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from api.core.database import get_session
from api.deps import CurrentUser, require_student
from api.models.score import StudentScore
from api.schemas.submission import StudentScoreRead

router = APIRouter(prefix="/scores", tags=["Scores"])


@router.get(
    "/me",
    response_model=List[StudentScoreRead],
    summary="Get current student's consolidated scores per question",
)
def get_my_scores(
    current_student: CurrentUser = Depends(require_student),
    session: Session = Depends(get_session),
):
    scores = session.exec(
        select(StudentScore).where(StudentScore.student_id == current_student.id)
    ).all()
    return scores
