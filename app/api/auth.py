from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import User
from app.auth.security import verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Autenticação"])

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

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    clean_email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos."
        )
    
    token = create_access_token(
        data={"sub": user.id, "email": user.email, "role": user.role, "name": user.name}
    )
    
    user_data = UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        score=user.score or 0,
        solvedCount=user.solved_count or 0,
        streakDays=user.streak_days or 1
    )
    
    return LoginResponse(user=user_data, token=token)

@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        score=user.score or 0,
        solvedCount=user.solved_count or 0,
        streakDays=user.streak_days or 1
    )
