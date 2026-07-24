from fastapi import APIRouter, Depends, Request, Response, HTTPException, Cookie, status
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal
from schemas.onboarding import (
    VerifyRequest,
    VerifyResponse,
    OnboardingSubmitRequest,
    OnboardingSubmitResponse,
)
from services.onboarding_service import OnboardingService
from models.onboarding_session import OnboardingSession

router = APIRouter(prefix="/api/v1/public/onboarding", tags=["onboarding"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_enabled():
    if not settings.ENABLE_ONBOARDING:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Onboarding is not enabled")


def get_onboarding_session(
    request: Request,
    db: Session = Depends(get_db),
) -> OnboardingSession:
    session_token = request.cookies.get(OnboardingService.ONBOARDING_COOKIE)
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No onboarding session")
    return OnboardingService.get_session(db, session_token)


def verify_csrf(
    request: Request,
    session: OnboardingSession = Depends(get_onboarding_session),
):
    csrf_token = request.headers.get("X-CSRF-Token")
    if not csrf_token:
        csrf_token = request.cookies.get(OnboardingService.CSRF_COOKIE)
    if csrf_token:
        OnboardingService.validate_csrf(session, csrf_token)
    return session


@router.post("/verify", response_model=VerifyResponse, dependencies=[Depends(check_enabled)])
def verify_invite(
    body: VerifyRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    result = OnboardingService.verify_token(db, body.token)

    secure = settings.ENV == "prod"
    max_age = OnboardingService.SESSION_TTL_HOURS * 3600

    response.set_cookie(
        key=OnboardingService.ONBOARDING_COOKIE,
        value=result["session_token"],
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        key=OnboardingService.CSRF_COOKIE,
        value=result["csrf_token"],
        httponly=False,
        secure=secure,
        samesite="lax",
        max_age=max_age,
        path="/",
    )

    return VerifyResponse(
        agency={"id": result["agency"]["id"], "name": result["agency"]["name"]},
        message="Token verified successfully",
    )


@router.post("/submit", response_model=OnboardingSubmitResponse, dependencies=[Depends(check_enabled)])
def submit_onboarding(
    body: OnboardingSubmitRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    session_token = request.cookies.get(OnboardingService.ONBOARDING_COOKIE)
    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No onboarding session")

    session = OnboardingService.get_session(db, session_token)

    csrf_token = request.headers.get("X-CSRF-Token")
    if csrf_token:
        OnboardingService.validate_csrf(session, csrf_token)

    result = OnboardingService.submit_onboarding(
        db,
        session,
        name=body.name,
        phone=body.phone,
        business_type=body.business_type,
        is_micro=body.is_micro,
    )

    response.delete_cookie(key=OnboardingService.ONBOARDING_COOKIE, path="/")
    response.delete_cookie(key=OnboardingService.CSRF_COOKIE, path="/")

    return OnboardingSubmitResponse(
        application_id=result["application_id"],
        merchant_id=result["merchant_id"],
        status=result["status"],
    )
