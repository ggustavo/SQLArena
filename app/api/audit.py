from decimal import Decimal
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.models import User, Question
from app.database.session import get_db
from app.api.deps import get_current_user, require_instructor
from app.dynamodb.dynamo_manager import DynamoDBManager

router = APIRouter(prefix="/audit", tags=["Auditoria"])

dynamo_manager = DynamoDBManager()


def _decimal_to_float(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decimal_to_float(v) for v in obj]
    return obj


class AuditLogItem(BaseModel):
    action_type: str
    entity_id: str
    details: Optional[Any] = None
    user_id: Optional[str] = None


@router.get("/dynamodb/submissions")
def get_dynamo_submission_logs(
    limit: int = Query(default=30, ge=1, le=100),
    user: User = Depends(require_instructor),
    db: Session = Depends(get_db),
):
    """
    Retorna os últimos N registros de submissões e execuções do Amazon DynamoDB
    (sqlarena-submissions-log) para auditoria interna de instrutores/administradores,
    incluindo percentual de CPU Linux capturado pelo Worker, tempo de execução e status.
    """
    try:
        table = dynamo_manager.table
        resp = table.scan(Limit=max(limit * 3, 60))
        items = resp.get("Items", [])
        items.sort(key=lambda x: str(x.get("created_at", "")), reverse=True)
        items = items[:limit]

        user_ids = {item.get("student_id") for item in items if item.get("student_id")}
        user_map = {}
        if user_ids:
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            user_map = {u.id: u.name for u in users}

        question_ids = set()
        for item in items:
            qid = item.get("question_id")
            if qid:
                try:
                    question_ids.add(int(qid))
                except (ValueError, TypeError):
                    pass
        question_map = {}
        if question_ids:
            questions = db.query(Question).filter(Question.id.in_(question_ids)).all()
            question_map = {q.id: q.title for q in questions}

        formatted = []
        for it in items:
            clean = _decimal_to_float(it)
            sid = clean.get("student_id")
            qid_raw = clean.get("question_id")
            try:
                qid = int(qid_raw)
            except (ValueError, TypeError):
                qid = qid_raw
            clean["student_name"] = user_map.get(sid, sid)
            clean["question_title"] = question_map.get(qid, f"Questão #{qid}" if qid else "N/A")
            formatted.append(clean)
        return formatted
    except Exception:
        return []


@router.get("/dynamodb/crud")
def get_dynamo_crud_logs(
    limit: int = Query(default=30, ge=1, le=100),
    user: User = Depends(require_instructor),
    db: Session = Depends(get_db),
):
    """
    Retorna os últimos N registros de auditoria de ações CRUD do Amazon DynamoDB
    (sqlarena-crud-actions-log) para instrutores/administradores.
    """
    try:
        table = dynamo_manager.crud_table
        resp = table.scan(Limit=max(limit * 3, 60))
        items = resp.get("Items", [])
        items.sort(key=lambda x: str(x.get("created_at", "") or x.get("timestamp", "")), reverse=True)
        items = items[:limit]

        user_ids = {item.get("user_id") for item in items if item.get("user_id")}
        user_map = {}
        if user_ids:
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            user_map = {u.id: u.name for u in users}

        formatted = []
        for it in items:
            clean = _decimal_to_float(it)
            uid = clean.get("user_id")
            clean["user_name"] = user_map.get(uid, uid)
            formatted.append(clean)
        return formatted
    except Exception:
        return []


@router.get("/logs")
def get_audit_logs(
    limit: int = 50,
    user: User = Depends(require_instructor)
):
    """Retorna logs de auditoria de ações administrativas (Instrutor)."""
    try:
        table = dynamo_manager.crud_table
        resp = table.scan(Limit=limit)
        items = resp.get("Items", [])
        items.sort(key=lambda x: str(x.get("timestamp", "") or x.get("created_at", "")), reverse=True)
        return [_decimal_to_float(it) for it in items[:limit]]
    except Exception:
        return []


@router.post("/logs")
def create_audit_log(
    payload: AuditLogItem,
    user: User = Depends(get_current_user)
):
    """Grava um registro de auditoria no DynamoDB."""
    try:
        action_id = dynamo_manager.log_crud_action(
            action_type=payload.action_type,
            entity_id=payload.entity_id,
            user_id=user.id,
            details=payload.details
        )
        return {"action_id": action_id, "status": "recorded"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

