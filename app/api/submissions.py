import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.config import settings
from app.database.session import get_db
from app.database.models import User, Question, UserSolvedQuestion
from app.api.deps import get_current_user
from app.cache.redis_client import redis_client
from app.sqs.queue_manager import SQSQueueManager
from app.dynamodb.dynamo_manager import DynamoDBManager

router = APIRouter(prefix="/submissions", tags=["Submissões"])

sqs_manager = SQSQueueManager()
dynamo_manager = DynamoDBManager()

class SubmitQueryRequest(BaseModel):
    questionId: Optional[int] = None
    question_id: Optional[int] = None
    query: Optional[str] = None
    sql_query: Optional[str] = None
    difficulty: Optional[str] = "Médio"
    questionTitle: Optional[str] = ""

class SubmissionCallbackRequest(BaseModel):
    submission_id: Optional[str] = None
    submissionId: Optional[str] = None
    user_id: Optional[str] = None
    userId: Optional[str] = None
    question_id: Optional[int] = None
    questionId: Optional[int] = None
    status: str = "DONE"
    outcome: str = "SUCCESS"
    is_correct: Optional[bool] = None
    isCorrect: Optional[bool] = None
    execution_time_ms: Optional[float] = 0.0
    executionTimeMs: Optional[float] = 0.0
    error_message: Optional[str] = None
    errorMessage: Optional[str] = None
    columns: List[str] = []
    rows: List[Dict[str, Any]] = []
    student_hash: Optional[str] = None
    studentHash: Optional[str] = None

@router.post("", status_code=status.HTTP_202_ACCEPTED)
def submit_query(
    payload: SubmitQueryRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submete uma consulta SQL para avaliação assíncrona.
    - Aplica Rate Limit global de 5 segundos via Redis (Requisito 8).
    - Despacha o payload para a fila Amazon SQS.
    - Grava o estado inicial no Redis e no DynamoDB.
    - Retorna HTTP 202 com submissionId para polling do frontend.
    """
    # 1. Validação de Rate Limit (5 segundos por aluno)
    allowed, ttl = redis_client.check_rate_limit(user.id, limit_seconds=5)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit excedido (5s). Aguarde {ttl} segundo(s) para enviar novamente."
        )

    # 2. Resolução flexível de campos (camelCase e snake_case)
    qid = payload.questionId if payload.questionId is not None else payload.question_id
    if qid is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O campo 'questionId' ou 'question_id' é obrigatório."
        )

    clean_query = (payload.query or payload.sql_query or "").strip()
    if not clean_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A consulta SQL não pode estar vazia."
        )

    # Verifica se a questão existe
    q = db.query(Question).filter(Question.id == qid).first()
    if not q:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Questão #{qid} não encontrada."
        )

    submission_id = f"sub_{uuid.uuid4().hex[:12]}"
    now_iso = datetime.now(timezone.utc).isoformat()

    sub_data: Dict[str, Any] = {
        "submissionId": submission_id,
        "userId": user.id,
        "studentId": user.id,
        "questionId": qid,
        "questionTitle": payload.questionTitle or q.title,
        "difficulty": payload.difficulty or q.difficulty,
        "query": clean_query,
        "status": "PROCESSING",
        "outcome": "PROCESSING",
        "pointsAwarded": 0,
        "executionTimeMs": None,
        "errorMessage": None,
        "columns": [],
        "rows": [],
        "createdAt": now_iso,
    }

    # 3. Grava no Redis para polling imediato
    redis_client.set_submission_status(submission_id, sub_data)

    # 4. Grava no DynamoDB (tabela sqlarena-submissions-log)
    try:
        dynamo_manager.record_submission(sub_data)
    except Exception as e:
        # Não trava se DynamoDB local falhar momentaneamente
        pass

    # 5. Publica na fila SQS
    try:
        sqs_manager.send_message(
            payload={
                "submission_id": submission_id,
                "user_id": user.id,
                "question_id": qid,
                "query": clean_query,
                "timestamp": now_iso,
            },
            attributes={"event_type": "STUDENT_SUBMISSION"}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao despachar submissão para a fila SQS: {e}"
        )

    return {
        "submissionId": submission_id,
        "status": "PROCESSING",
        "pollIntervalMs": 1000
    }

@router.post("/callback", status_code=status.HTTP_200_OK)
def process_submission_callback(
    payload: SubmissionCallbackRequest,
    x_internal_key: Optional[str] = Header(None, alias="x-internal-key"),
    db: Session = Depends(get_db)
):
    """
    Endpoint interno chamado pelos Workers via HTTP/ALB ao concluir a avaliação.
    - O Worker avalia 100% no PostgreSQL Local da sua EC2 e repassa o resultado para este endpoint.
    - O Backend centraliza todas as interações com o RDS, Redis e DynamoDB:
      1. Se isCorrect: concede +10 XP no RDS e registra em user_solved_questions.
      2. Atualiza o status da submissão no Redis para o polling do frontend.
      3. Atualiza o resultado final no Amazon DynamoDB.
    """
    # Validação de segurança básica da chave interna
    if settings.INTERNAL_API_KEY and x_internal_key and x_internal_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chave de comunicação interna inválida."
        )

    sub_id = payload.submission_id or payload.submissionId
    uid = payload.user_id or payload.userId
    qid = payload.question_id if payload.question_id is not None else payload.questionId
    is_correct = payload.is_correct if payload.is_correct is not None else (payload.isCorrect or False)
    exec_time = payload.execution_time_ms if payload.execution_time_ms is not None else (payload.executionTimeMs or 0.0)
    err_msg = payload.error_message or payload.errorMessage
    student_hash = payload.student_hash or payload.studentHash

    points_awarded = 0

    # 1. Se acerto inédito: pontua +10 XP no RDS
    if is_correct and uid and qid:
        try:
            solved = db.query(UserSolvedQuestion).filter_by(
                user_id=uid,
                question_id=int(qid)
            ).first()

            if not solved:
                db.add(UserSolvedQuestion(user_id=uid, question_id=int(qid)))
                user = db.query(User).filter(User.id == uid).first()
                if user:
                    user.score = (user.score or 0) + 10
                    user.solved_count = (user.solved_count or 0) + 1
                db.commit()
                redis_client.invalidate_ranking()
                points_awarded = 10
        except Exception as ex:
            db.rollback()

    # 2. Atualiza status no Redis para polling do frontend
    final_data = {
        "submissionId": sub_id,
        "userId": uid,
        "questionId": qid,
        "status": "DONE",
        "outcome": payload.outcome,
        "pointsAwarded": points_awarded,
        "executionTimeMs": exec_time,
        "errorMessage": err_msg,
        "columns": payload.columns,
        "rows": payload.rows,
        "strictModeHashMatched": is_correct,
        "finishedAt": datetime.now(timezone.utc).isoformat(),
    }
    if sub_id:
        redis_client.set_submission_status(sub_id, final_data)

    # 3. Atualiza registro no DynamoDB
    if sub_id:
        try:
            dynamo_manager.update_submission_result(
                submission_id=sub_id,
                status=payload.outcome,
                is_correct=is_correct,
                execution_time_ms=exec_time,
                error_message=err_msg,
                answer_hash=student_hash
            )
        except Exception:
            pass

    return {
        "success": True,
        "submissionId": sub_id,
        "pointsAwarded": points_awarded
    }

@router.get("/{submission_id}/status")
def get_submission_status(
    submission_id: str,
    user: User = Depends(get_current_user)
):
    """
    Retorna o status atual de uma submissão para polling.
    Prioriza consulta ultrarrápida no Redis; fallback para DynamoDB.
    """
    # 1. Consulta no Redis
    cached = redis_client.get_submission_status(submission_id)
    if cached:
        return cached

    # 2. Fallback no DynamoDB
    try:
        doc = dynamo_manager.get_submission(submission_id)
        if doc:
            return doc
    except Exception:
        pass

    # Se ainda não encontrou nem no Redis nem no Dynamo
    return {
        "submissionId": submission_id,
        "status": "PROCESSING",
        "outcome": "PROCESSING",
        "columns": [],
        "rows": [],
        "errorMessage": None,
    }

def _format_submission_item(s: Dict[str, Any], db: Session) -> Dict[str, Any]:
    sub_id = s.get("submission_id") or s.get("submissionId")
    q_id_raw = s.get("question_id") or s.get("questionId")
    try:
        q_id = int(q_id_raw)
    except (ValueError, TypeError):
        q_id = q_id_raw

    q_title = s.get("questionTitle")
    diff = s.get("difficulty")
    if not q_title and q_id:
        q = db.query(Question).filter(Question.id == q_id).first()
        if q:
            q_title = q.title
            diff = q.difficulty

    status_val = s.get("status", "DONE")
    is_correct = bool(s.get("is_correct", False))
    outcome = s.get("outcome") or ("SUCCESS" if is_correct or status_val == "SUCCESS" else status_val)
    created = s.get("created_at") or s.get("createdAt")
    exec_time = s.get("execution_time_ms") or s.get("executionTimeMs")
    if exec_time is not None:
        exec_time = float(exec_time)

    return {
        "submissionId": sub_id,
        "submission_id": sub_id,
        "questionId": q_id,
        "question_id": q_id,
        "questionTitle": q_title or f"Questão #{q_id}",
        "difficulty": diff or "Médio",
        "userId": s.get("student_id") or s.get("userId"),
        "query": s.get("query", ""),
        "status": "DONE" if status_val not in ["PROCESSING", "QUEUED"] else status_val,
        "outcome": outcome,
        "errorMessage": s.get("pg_error") or s.get("errorMessage"),
        "executionTimeMs": exec_time,
        "strictModeHashMatched": is_correct or outcome == "SUCCESS",
        "createdAt": created,
        "pointsAwarded": 10 if outcome == "SUCCESS" else 0,
        "columns": s.get("columns", []),
        "rows": s.get("rows", []),
    }

@router.get("/history")
def get_history(
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna o histórico de submissões do aluno autenticado a partir do DynamoDB."""
    try:
        submissions = dynamo_manager.get_student_submissions(user.id)
    except Exception:
        submissions = []

    formatted = [_format_submission_item(s, db) for s in submissions]

    # Aplica filtros opcionais
    filtered = []
    for s in formatted:
        if search:
            s_clean = search.strip().lower()
            q_title = str(s.get("questionTitle", "")).lower()
            q_query = str(s.get("query", "")).lower()
            q_id = str(s.get("questionId", ""))
            if s_clean not in q_title and s_clean not in q_query and s_clean != q_id:
                continue

        if status_filter and status_filter != "ALL":
            outcome = s.get("outcome", "")
            st = s.get("status", "")
            if outcome != status_filter and st != status_filter:
                continue

        filtered.append(s)

    # Ordena pelos mais recentes
    filtered.sort(key=lambda x: str(x.get("createdAt", "")), reverse=True)
    return filtered

@router.get("/recent")
def get_recent(
    limit: int = 5,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retorna as N submissões mais recentes do aluno autenticado."""
    try:
        submissions = dynamo_manager.get_student_submissions(user.id)
        formatted = [_format_submission_item(s, db) for s in submissions]
        formatted.sort(key=lambda x: str(x.get("createdAt", "")), reverse=True)
        return formatted[:limit]
    except Exception:
        return []

@router.get("/last")
def get_last_submission(
    question_id: int,
    user: User = Depends(get_current_user)
):
    """
    Retorna a última consulta SQL submetida pelo aluno para uma questão específica,
    permitindo restaurar o editor SQL exatamente como ele deixou.
    """
    try:
        submissions = dynamo_manager.get_student_submissions(user.id, limit=50)
        q_subs = [
            s for s in submissions 
            if str(s.get("question_id") or s.get("questionId")) == str(question_id)
        ]
        if not q_subs:
            return {"query": None}
        q_subs.sort(key=lambda x: str(x.get("created_at") or x.get("createdAt") or ""), reverse=True)
        last_query = q_subs[0].get("query", "")
        return {"query": last_query if last_query else None}
    except Exception as e:
        return {"query": None}
