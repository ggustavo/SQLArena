"""
Rotas de auditoria (log de CRUD), consumidas por app/frontend/src/services/auditService.js.

Nota sobre o payload: o frontend manda um campo `details` (texto livre), enquanto
o DynamoDBManager.log_crud_action usa `changed_data` (dicionário estruturado).
Resolvemos isso aqui, mapeando details -> changed_data.details, sem precisar
mudar o frontend nem o dynamo_manager.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.backend.dependencies import get_dynamo_manager
from app.dynamodb.dynamo_manager import DynamoDBManager

router = APIRouter()


class AuditLogIn(BaseModel):
    action_type: str
    entity: str = "exercise"
    entity_id: str
    user_id: str = "sistema"
    details: Optional[str] = None
    # action_id e created_at, se vierem do frontend, são ignorados de propósito:
    # o backend é a fonte da verdade e gera os dois de forma consistente.


@router.get("/logs")
def get_logs(limit: int = 50, dynamo: DynamoDBManager = Depends(get_dynamo_manager)):
    return dynamo.list_crud_actions(limit=limit)


@router.post("/logs", status_code=201)
def create_log(payload: AuditLogIn, dynamo: DynamoDBManager = Depends(get_dynamo_manager)):
    dynamo.ensure_crud_table_exists()
    return dynamo.log_crud_action(
        action_type=payload.action_type,
        entity=payload.entity,
        entity_id=payload.entity_id,
        user_id=payload.user_id,
        changed_data={"details": payload.details} if payload.details else None,
    )
