from dataclasses import dataclass
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from core.security import verify_token
from services.auth_service import get_current_user as get_user_from_db


@dataclass
class UserContext:
    role: str = "merchant"
    agency_id: int | None = None
    user_id: int = 1

    def require_super_admin(self):
        if self.role != "super_admin":
            raise HTTPException(403, "Requires super_admin")

    def require_agent(self):
        if self.role not in ("agent_admin", "super_admin"):
            raise HTTPException(403, "Requires agent or super_admin")

    def require_merchant_owner(self, target_user_id: int):
        if self.role == "super_admin":
            return
        if self.role == "merchant" and self.user_id != target_user_id:
            raise HTTPException(404, "Resource not found")

    def tenant_filter(self, model_class):
        if self.role == "super_admin":
            return True
        if self.role in ("agent_admin",):
            return model_class.agency_id == self.agency_id
        if self.role == "merchant":
            from sqlalchemy import and_
            return and_(
                model_class.agency_id == self.agency_id,
                model_class.user_id == self.user_id,
            )
        return False


def get_current_user(request, db):
    trusted_user = (request.headers.get("X-Authenticated-User") or "").strip()
    if not trusted_user:
        raise HTTPException(401, "Not authenticated")
    from models.user import User
    user = db.query(User).filter(User.openid == f"h5:{trusted_user}").first()
    if not user:
        raise HTTPException(401, "User not found")
    return UserContext(
        role=user.role or "merchant",
        agency_id=user.agency_id,
        user_id=user.id,
    )


security = HTTPBearer(auto_error=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_user_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> UserContext:
    token = (
        credentials.credentials
        if credentials is not None
        else request.cookies.get(settings.H5_COOKIE_NAME)
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = verify_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user = get_user_from_db(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return UserContext(
        role=getattr(user, "role", "merchant"),
        agency_id=getattr(user, "agency_id", None),
        user_id=user.id,
    )
