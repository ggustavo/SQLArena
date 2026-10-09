import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import User
from app.auth.security import verify_password, create_access_token, get_password_hash
from app.api.deps import get_current_user
from app.dynamodb.dynamo_manager import DynamoDBManager
from app.cache.redis_client import redis_client

router = APIRouter(prefix="/auth", tags=["Autenticação"])
logger = logging.getLogger(__name__)

class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Informe seu nome.")
        return value

    @field_validator("password")
    @classmethod
    def check_password_length(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("A senha deve ter no máximo 72 bytes.")
        return value

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    score: int
    solvedCount: int
    streakDays: int

class LoginResponse(BaseModel):
    user: UserResponse
    token: str

def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id, name=user.name, email=user.email, role=user.role,
        score=user.score or 0, solvedCount=user.solved_count or 0,
        streakDays=user.streak_days or 0,
    )

def login_response(user: User) -> LoginResponse:
    token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role, "name": user.name}
    )
    return LoginResponse(user=user_response(user), token=token)

@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = str(payload.email).strip().lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")

    user = User(
        id=f"user_{uuid.uuid4().hex}", name=payload.name, email=email,
        password_hash=get_password_hash(payload.password), role="STUDENT",
        score=0, solved_count=0, streak_days=0,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
    db.refresh(user)
    redis_client.invalidate_ranking()
    try:
        DynamoDBManager().log_crud_action(
            action_type="USER_REGISTER", entity="user", entity_id=user.id,
            user_id=user.id, changed_data={"name": user.name, "email": user.email, "role": user.role},
        )
    except Exception:
        logger.exception("Falha ao auditar cadastro do usuário %s", user.id)
    return login_response(user)

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    clean_email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos."
        )
    
    return login_response(user)

@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return user_response(user)
