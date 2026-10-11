import io
import logging
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from PIL import Image, ImageOps
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
from app.s3.s3_manager import S3Manager

router = APIRouter(prefix="/users", tags=["Usuários"])
logger = logging.getLogger(__name__)


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    currentPassword: str | None = None
    university: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, max_length=80)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Informe seu nome.")
        return value

    @field_validator("university", "city", "state", "country")
    @classmethod
    def clean_optional_strings(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                return None
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

    db_user = db.query(User).filter(User.id == user.id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    changes = {}
    if payload.name is not None and payload.name != db_user.name:
        changes["name"] = {"before": db_user.name, "after": payload.name}
        db_user.name = payload.name
    if payload.email is not None:
        email = str(payload.email).strip().lower()
        if email != db_user.email:
            if db.query(User).filter(func.lower(User.email) == email, User.id != db_user.id).first():
                raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
            changes["email"] = {"before": db_user.email, "after": email}
            db_user.email = email
    if payload.password:
        db_user.password_hash = get_password_hash(payload.password)
        changes["password"] = "changed"

    for field_name in ("university", "city", "state", "country"):
        if field_name in payload.model_fields_set:
            new_val = getattr(payload, field_name)
            old_val = getattr(db_user, field_name)
            if new_val != old_val:
                changes[field_name] = {"before": old_val, "after": new_val}
                setattr(db_user, field_name, new_val)

    if changes:
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
        db.refresh(db_user)
        redis_client.delete_user_brief(db_user.id)
        redis_client.delete_cached_auth_user(db_user.id)
        if "name" in changes:
            redis_client.invalidate_ranking()
        audit_user("USER_UPDATE", db_user.id, db_user, changes)
    return user_response(db_user)


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Upload e manipulação de arquivo binário de imagem de perfil (avatar).
    A imagem é redimensionada (rescaling 256x256) com Pillow e armazenada no Amazon S3.
    Operação auditada no Amazon DynamoDB.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="O arquivo enviado deve ser uma imagem válida (PNG, JPG, WEBP).",
        )

    raw_bytes = await file.read()
    if len(raw_bytes) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="A imagem excede o tamanho máximo de 5MB.")

    # Manipulação do arquivo binário (Rescaling com Pillow)
    try:
        image = Image.open(io.BytesIO(raw_bytes))
        image = ImageOps.exif_transpose(image)
        if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
            image = image.convert("RGBA")
        else:
            image = image.convert("RGB")
        image.thumbnail((256, 256), Image.Resampling.LANCZOS)

        output_buffer = io.BytesIO()
        image.save(output_buffer, format="PNG", optimize=True)
        processed_bytes = output_buffer.getvalue()
    except Exception as img_err:
        logger.exception("Falha ao manipular arquivo binário de imagem: %s", img_err)
        raise HTTPException(status_code=400, detail="Formato de imagem inválido ou corrompido.")

    s3_key = f"avatars/{user.id}.png"
    try:
        S3Manager().upload_file(s3_key, processed_bytes, content_type="image/png")
    except Exception as s3_err:
        logger.exception("Falha ao salvar avatar no S3: %s", s3_err)
        raise HTTPException(status_code=500, detail="Falha ao salvar avatar no Amazon S3.")

    avatar_url = f"/api/users/{user.id}/avatar"
    db_user = db.query(User).filter(User.id == user.id).first()
    if db_user:
        db_user.avatar_url = avatar_url
        db.commit()
        db.refresh(db_user)
        user_to_return = db_user
    else:
        user_to_return = user

    redis_client.delete_user_brief(user.id)
    redis_client.delete_cached_auth_user(user.id)
    redis_client.invalidate_ranking()

    audit_user("USER_AVATAR_UPLOAD", user.id, user_to_return, {
        "s3_key": s3_key,
        "size_bytes": len(processed_bytes),
        "dimensions": f"{image.width}x{image.height}",
        "action": "image_rescaling_lanczos_256",
    })
    return user_response(user_to_return)


@router.get("/{user_id}/avatar")
def get_user_avatar(
    user_id: str,
    t: str | None = Query(default=None),
):
    """
    Recupera o arquivo binário do avatar do usuário armazenado no Amazon S3.
    """
    s3_key = f"avatars/{user_id}.png"
    s3 = S3Manager()
    try:
        if not s3.file_exists(s3_key):
            raise HTTPException(status_code=404, detail="Avatar não encontrado.")
        avatar_bytes = s3.read_file_bytes(s3_key)
        return Response(
            content=avatar_bytes,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=300, must-revalidate",
                "Access-Control-Allow-Origin": "*",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Erro ao buscar avatar no S3 para usuário %s: %s", user_id, e)
        raise HTTPException(status_code=404, detail="Avatar não encontrado.")


@router.delete("/me/avatar", response_model=UserResponse)
def delete_my_avatar(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Remove o avatar do usuário do Amazon S3 e limpa a referência no RDS.
    Auditado no DynamoDB.
    """
    s3_key = f"avatars/{user.id}.png"
    try:
        S3Manager().delete_file(s3_key)
    except Exception as s3_err:
        logger.warning("Falha ao remover arquivo do avatar no S3: %s", s3_err)

    db_user = db.query(User).filter(User.id == user.id).first()
    if db_user:
        db_user.avatar_url = None
        db.commit()
        db.refresh(db_user)
        user_to_return = db_user
    else:
        user_to_return = user

    redis_client.delete_user_brief(user.id)
    redis_client.delete_cached_auth_user(user.id)
    redis_client.invalidate_ranking()
    audit_user("USER_AVATAR_DELETE", user.id, user_to_return, {"s3_key": s3_key})
    return user_response(user_to_return)


@router.delete("/me", status_code=status.HTTP_200_OK)
def delete_my_account(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Exclui a conta do próprio usuário (DELETE do CRUD de Usuários).
    Remove o avatar no S3 e audita a exclusão no DynamoDB.
    """
    if user.avatar_url:
        try:
            S3Manager().delete_file(f"avatars/{user.id}.png")
        except Exception:
            pass

    user_data = {"id": user.id, "name": user.name, "email": user.email, "role": user.role}
    audit_user("USER_DELETE", user.id, user, user_data)

    db_user = db.query(User).filter(User.id == user.id).first()
    if db_user:
        db.delete(db_user)
        db.commit()

    redis_client.delete_user_brief(user.id)
    redis_client.delete_cached_auth_user(user.id)
    redis_client.invalidate_ranking()
    return {"detail": "Conta excluída com sucesso."}


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


@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Consulta os dados de um usuário pelo ID (READ do CRUD).
    """
    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return user_response(target)


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


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    instructor: User = Depends(require_instructor),
):
    """
    Exclui um usuário do sistema (DELETE no CRUD de Usuários para instrutor).
    Remove o avatar no S3 e audita a exclusão no DynamoDB.
    """
    if user_id == instructor.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir sua própria conta através deste painel.")

    target = db.query(User).filter(User.id == user_id).first()
    if target is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if target.avatar_url:
        try:
            S3Manager().delete_file(f"avatars/{target.id}.png")
        except Exception:
            pass

    user_data = {"id": target.id, "name": target.name, "email": target.email, "role": target.role}
    audit_user("USER_DELETE", instructor.id, target, user_data)

    db.delete(target)
    db.commit()
    redis_client.invalidate_ranking()
    return {"detail": f"Usuário {target.name} removido com sucesso."}
