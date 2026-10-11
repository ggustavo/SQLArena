from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.database.models import User
from app.auth.security import decode_access_token
from app.cache.redis_client import redis_client

security_bearer = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token com payload corrompido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Consulta em memória no Redis (elimina 95% do overhead sobre o pool do PostgreSQL)
    cached = redis_client.get_cached_auth_user(user_id)
    if cached:
        return User(**cached)
    
    # 2. Fallback no banco PostgreSQL RDS
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Popula cache Redis para as próximas requisições
    redis_client.set_cached_auth_user(user_id, {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "password_hash": user.password_hash,
        "role": user.role,
        "score": user.score or 0,
        "solved_count": user.solved_count or 0,
        "streak_days": user.streak_days or 0,
        "avatar_url": user.avatar_url,
        "university": user.university,
        "city": user.city,
        "state": user.state,
        "country": user.country,
    }, ttl=300)

    return user

def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        return None
    try:
        return get_current_user(credentials, db)
    except HTTPException:
        return None

def require_instructor(user: User = Depends(get_current_user)) -> User:
    if user.role != "INSTRUCTOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a instrutores.",
        )
    return user
