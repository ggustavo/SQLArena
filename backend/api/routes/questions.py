from typing import List, Optional
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlmodel import Session, select
from api.core.cache import CacheService
from api.core.database import get_session
from api.deps import CurrentUser, get_current_user, require_teacher
from api.models.question import Question, QuestionStatus
from api.schemas.question import (
    QuestionCatalogItem,
    QuestionDetailStudent,
    QuestionDetailTeacher,
)
from api.services.question_provisioner import QuestionProvisioner
from api.services.storage_service import StorageService

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.post(
    "",
    response_model=QuestionDetailTeacher,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new SQL exercise with DDL and DML scripts (Teacher only)",
)
async def create_question(
    background_tasks: BackgroundTasks,
    title: str = Form(..., description="Exercise Title"),
    context: str = Form(..., description="Problem description & schema context"),
    expected_query: str = Form(..., description="Teacher's reference SQL query"),
    timeout_seconds: int = Form(5, ge=1, le=60, description="Query timeout in seconds"),
    ddl_file: UploadFile = File(..., description="DDL .sql script"),
    dml_file: Optional[UploadFile] = File(None, description="Optional DML .sql script"),
    current_teacher: CurrentUser = Depends(require_teacher),
    session: Session = Depends(get_session),
):
    ddl_bytes = await ddl_file.read()
    if not ddl_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="DDL file cannot be empty")

    dml_bytes = await dml_file.read() if dml_file else None

    # 1. Create initial question entity in RDS 1
    question = Question(
        title=title,
        context=context,
        expected_query=expected_query,
        timeout_seconds=timeout_seconds,
        status=QuestionStatus.CREATING_TABLES,
        created_by=current_teacher.id,
    )
    session.add(question)
    session.commit()
    session.refresh(question)

    # 2. Upload SQL scripts to S3
    s3_ddl_key = f"questions/{question.id}/ddl.sql"
    StorageService.upload_sql_file(ddl_bytes, s3_ddl_key)
    question.s3_ddl_key = s3_ddl_key

    s3_dml_key = None
    if dml_bytes:
        s3_dml_key = f"questions/{question.id}/dml.sql"
        StorageService.upload_sql_file(dml_bytes, s3_dml_key)
        question.s3_dml_key = s3_dml_key

    session.add(question)
    session.commit()
    session.refresh(question)

    # 3. Trigger asynchronous background task to provision RDS 2 schema
    background_tasks.add_task(
        QuestionProvisioner.provision_in_rds2,
        question.id,
        s3_ddl_key,
        s3_dml_key,
    )

    return question


@router.get(
    "",
    response_model=List[QuestionCatalogItem],
    summary="Get questions catalog (Cache-Aside via Redis)",
)
def get_catalog(
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    cache_key = "cache:questions:catalog"

    # Step 1: Check ElastiCache (Redis)
    cached_catalog = CacheService.get(cache_key)
    if cached_catalog is not None:
        return cached_catalog

    # Step 2: Cache Miss -> Query RDS 1
    questions = session.exec(select(Question).where(Question.status == QuestionStatus.READY)).all()
    catalog = [
        QuestionCatalogItem(
            id=q.id,
            title=q.title,
            timeout_seconds=q.timeout_seconds,
            status=q.status,
        ).model_dump()
        for q in questions
    ]

    # Step 3: Populate Redis with TTL
    CacheService.set(cache_key, catalog)
    return catalog


@router.get(
    "/{question_id}",
    response_model=QuestionDetailStudent,
    summary="Get question context for students (Cache-Aside via Redis)",
)
def get_question(
    question_id: int,
    current_user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    cache_key = f"cache:question:{question_id}"

    # Step 1: Check ElastiCache (Redis)
    cached_data = CacheService.get(cache_key)
    if cached_data is not None:
        return cached_data

    # Step 2: Cache Miss -> Query RDS 1
    question = session.get(Question, question_id)
    if not question or question.status != QuestionStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found or still being provisioned",
        )

    student_view = QuestionDetailStudent(
        id=question.id,
        title=question.title,
        context=question.context,
        timeout_seconds=question.timeout_seconds,
        status=question.status,
    ).model_dump()

    # Step 3: Populate Redis with TTL
    CacheService.set(cache_key, student_view)
    return student_view
