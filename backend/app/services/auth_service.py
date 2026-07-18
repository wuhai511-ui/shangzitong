"""Auth service — handles WeChat mock login and user operations."""
from sqlalchemy.orm import Session
from models.user import User
from core.security import create_access_token


def authenticate_or_create_user(db: Session, code: str) -> dict:
    """Mock WeChat login: use code as openid, find or create User.

    Args:
        db: Database session.
        code: WeChat login code. In dev mode, treated as openid.

    Returns:
        Dict with access_token, token_type, and user info.
    """
    user = db.query(User).filter(User.openid == code).first()
    if not user:
        user = User(
            openid=code,
            nickname=f"用户_{code[-6:]}",
            phone="",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(data={"user_id": user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "openid": user.openid,
            "nickname": user.nickname,
        },
    }


def get_current_user(db: Session, user_id: int) -> User | None:
    """Fetch user by id.

    Args:
        db: Database session.
        user_id: User id extracted from JWT.

    Returns:
        User instance or None.
    """
    return db.query(User).filter(User.id == user_id).first()
