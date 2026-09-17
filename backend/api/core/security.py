from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple
import bcrypt
import jwt
from api.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies plain password against bcrypt hash."""
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    """Generates bcrypt hash for plain password."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def create_stateless_access_token(user_id: int, email: str, role: str) -> Tuple[str, int]:
    """
    Generates a pure stateless JWT containing user identity and role.
    Verification requires only the SECRET_KEY, supporting horizontal ECS scaling.
    """
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    expire = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a stateless JWT access token."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
