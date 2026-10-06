from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from app.database.models import User
from app.api.deps import get_current_user, require_instructor
from app.dynamodb.dynamo_manager import DynamoDBManager

router = APIRouter(prefix="/audit", tags=["Auditoria"])

dynamo_manager = DynamoDBManager()

class AuditLogItem(BaseModel):
    action_type: str
    entity_id: str
    details: Optional[Any] = None
    user_id: Optional[str] = None

@router.get("/logs")
def get_audit_logs(
    limit: int = 50,
    user: User = Depends(require_instructor)
):
    """Retorna logs de auditoria de ações administrativas (Instrutor)."""
    # Consulta na tabela DynamoDB
    try:
        # Recupera as ações
        table = dynamo_manager.crud_table
        resp = table.scan(Limit=limit)
        items = resp.get("Items", [])
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return items
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
