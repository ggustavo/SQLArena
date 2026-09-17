import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from api.core.database import get_session
from api.deps import CurrentUser, require_student
from api.models.question import Question, QuestionStatus
from api.schemas.submission import SubmissionCreate, SubmissionAcceptedResponse
from api.services.queue_service import QueueService

router = APIRouter(prefix="/questions", tags=["Submissions"])


@router.post(
    "/{question_id}/submit",
    response_model=SubmissionAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit SQL answer for asynchronous grading (Student only)",
)
def submit_answer(
    question_id: int,
    submission_in: SubmissionCreate,
    current_student: CurrentUser = Depends(require_student),
    session: Session = Depends(get_session),
):
    question = session.get(Question, question_id)
    if not question or question.status != QuestionStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question is not available for submissions",
        )

    submission_id = str(uuid.uuid4())
    payload = {
        "submission_id": submission_id,
        "student_id": current_student.id,
        "question_id": question_id,
        "submitted_query": submission_in.query.strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    try:
        QueueService.publish_submission(payload)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue submission for evaluation: {str(e)}",
        )

    return SubmissionAcceptedResponse(
        submission_id=submission_id,
        status="accepted",
        message="Your SQL answer has been queued for evaluation.",
    )
