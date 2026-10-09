import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import UserResponse, user_response
from app.api.deps import get_current_user, require_instructor
from app.auth.security import get_password_hash, verify_password
from app.database.models import User
from app.database.session import get_db
from app.dynamodb.dynamo_manager import DynamoDBManager
from app.cache.redis_client import redis_client

router = APIRouter(prefix="/users", tags=["Usuários"])
logger = logging.getLogger(__name__)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    currentPassword: str | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Informe seu nome.")
        return value

    @model_validator(mode="after")
    def check_password_confirmation(self):
        if self.password and not self.currentPassword:
            raise ValueError("Informe a senha atual para alterar a senha.")
        if self.password and len(self.password.encode("utf-8")) > 72:
            raise ValueError("A senha deve ter no máximo 72 bytes.")
        return self


class RoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["STUDENT", "INSTRUCTOR"]


def audit_user(action_type: str, actor_id: str, target: User, changed_data: dict):
    try:
        DynamoDBManager().log_crud_action(
            action_type=action_type, entity="user", entity_id=target.id,
            user_id=actor_id, changed_data=changed_data,
        )
    except Exception:
        logger.exception("Falha ao auditar %s para usuário %s", action_type, target.id)


@router.put("/me", response_model=UserResponse)
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not payload.model_fields_set:
        raise HTTPException(status_code=400, detail="Informe pelo menos um campo para atualizar.")
    if payload.password and not verify_password(payload.currentPassword, user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta.")

    changes = {}
    if payload.name is not None and payload.name != user.name:
        changes["name"] = {"before": user.name, "after": payload.name}
        user.name = payload.name
    if payload.email is not None:
        email = str(payload.email).strip().lower()
        if email != user.email:
            if db.query(User).filter(func.lower(User.email) == email, User.id != user.id).first():
                raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
            changes["email"] = {"before": user.email, "after": email}
            user.email = email
    if payload.password:
        user.password_hash = get_password_hash(payload.password)
        changes["password"] = "changed"

    if changes:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
        db.refresh(user)
        if "name" in changes:
            redis_client.invalidate_ranking()
        audit_user("USER_UPDATE", user.id, user, changes)
    return user_response(user)


@router.get("", response_model=list[UserResponse])
def list_users(
    search: str = Query(default="", max_length=120),
    db: Session = Depends(get_db),
    instructor: User = Depends(require_instructor),
):
    query = db.query(User)
    if search.strip():
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(User.name.ilike(pattern), User.email.ilike(pattern)))
    return [user_response(user) for user in query.order_by(User.name.asc(), User.id.asc()).all()]


@router.patch("/{user_id}/role", response_model=UserResponse)
def update_role(
    user_id: str,
    payload: RoleUpdate,
    db: Session = Depends(get_db),
    instructor: User = Depends(require_instructor),
):
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if target.id == instructor.id and payload.role == "STUDENT":
        raise HTTPException(status_code=400, detail="Você não pode remover seu próprio acesso de instrutor.")
    if target.role != payload.role:
        previous_role = target.role
        target.role = payload.role
        db.commit()
        db.refresh(target)
        audit_user("PROMOTE_USER", instructor.id, target, {"role": {"before": previous_role, "after": target.role}})
    return user_response(target)
