from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from api.core.security import decode_access_token
from api.models.user import Role

security_bearer = HTTPBearer(auto_error=True)


class CurrentUser:
    """Authenticated user context extracted from pure stateless JWT."""
    def __init__(self, user_id: int, email: str, role: Role):
        self.id = user_id
        self.email = email
        self.role = role


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security_bearer)) -> CurrentUser:
    """Extracts and cryptographically validates pure stateless JWT token."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = int(payload.get("sub"))
        email = payload.get("email")
        role = Role(payload.get("role"))
        return CurrentUser(user_id=user_id, email=email, role=role)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
    except (jwt.PyJWTError, ValueError, KeyError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")


def require_teacher(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != Role.TEACHER:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only professors can access this resource")
    return current_user


def require_student(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != Role.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only students can access this resource")
    return current_user
