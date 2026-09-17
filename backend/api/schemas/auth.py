from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from api.models.user import Role


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    role: Role = Role.STUDENT


class UserRead(BaseModel):
    id: int
    email: EmailStr
    role: Role
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: Role
