"""Auth API routes — WeChat login and user info."""
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from core.config import settings
from core.database import SessionLocal
from core.security import verify_token
from schemas.auth import LoginRequest, LoginResponse, UserInfo
from services.auth_service import (
    authenticate_or_create_h5_user, authenticate_or_create_user, get_current_user,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def get_db():
    """FastAPI dependency: yield a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_dependency(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> UserInfo:
    """FastAPI dependency: extract and validate JWT, return user."""
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
    user = get_current_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return UserInfo.model_validate(user)


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Mock WeChat login. Uses code as openid, creates user if not exists."""
    return authenticate_or_create_user(db, request.code)


@router.post("/session", response_model=UserInfo)
def create_h5_session(
    response: Response,
    x_authenticated_user: str | None = Header(
        default=None, alias=settings.H5_TRUSTED_HEADER
    ),
    db: Session = Depends(get_db),
):
    """Create an H5 cookie session from the reverse proxy's trusted identity."""
    username = (x_authenticated_user or "").strip()
    if not username or len(username) > 124:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    session = authenticate_or_create_h5_user(db, username)
    max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    response.set_cookie(
        key=settings.H5_COOKIE_NAME,
        value=session["access_token"],
        httponly=True,
        secure=settings.ENV == "prod",
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="szt_csrf",
        value=csrf_token,
        httponly=False,
        secure=settings.ENV == "prod",
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    return session["user"]


@router.get("/me", response_model=UserInfo)
def me(current_user: UserInfo = Depends(get_current_user_dependency)):
    """Return the currently authenticated user's info."""
    return current_user
