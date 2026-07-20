"""Auth service — handles WeChat login and user operations."""
from sqlalchemy.orm import Session
from models.user import User
from core.security import create_access_token
from core.config import settings


def authenticate_or_create_user(db: Session, code: str) -> dict:
    """WeChat login: in dev uses code as openid; in prod calls WeChat API.

    Args:
        db: Database session.
        code: WeChat login code (dev=mock, prod=real).
    """
    if settings.ENV == "prod":
        openid = _wechat_code_to_openid(code)
    else:
        openid = code  # Dev: treat code as openid

    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(openid=openid, nickname=f"用户_{openid[-6:]}", phone="")
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(data={"user_id": user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "openid": user.openid, "nickname": user.nickname},
    }


def authenticate_or_create_h5_user(db: Session, username: str) -> dict:
    """Find or create the H5 user represented by a trusted proxy identity."""
    openid = f"h5:{username}"
    user = db.query(User).filter(User.openid == openid).first()
    if not user:
        user = User(openid=openid, nickname=f"H5_{username[-61:]}", phone="")
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token(data={"user_id": user.id})
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user.id, "openid": user.openid, "nickname": user.nickname},
    }


def _wechat_code_to_openid(code: str) -> str:
    """Call WeChat API to exchange code for openid."""
    import httpx
    resp = httpx.get(
        "https://api.weixin.qq.com/sns/jscode2session",
        params={
            "appid": settings.WECHAT_APPID,
            "secret": settings.WECHAT_SECRET,
            "js_code": code,
            "grant_type": "authorization_code",
        },
    )
    data = resp.json()
    if "openid" not in data:
        raise ValueError(f"WeChat login failed: {data.get('errmsg', 'unknown')}")
    return data["openid"]


def get_current_user(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()
