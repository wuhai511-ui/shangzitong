"""Merchant profile API routes."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from api.auth import get_current_user_dependency
from core.database import get_db
from models.merchant_profile import MerchantProfile
from schemas.auth import UserInfo
from schemas.profile import CashProfileResponse, CashProfileUpdate


router = APIRouter(prefix="/api/v1/profile", tags=["profile"])


def _response(profile: MerchantProfile | None) -> CashProfileResponse:
    if profile is None or profile.available_cash is None:
        return CashProfileResponse(
            available_cash=None,
            available_cash_updated_at=None,
            is_estimate=True,
        )

    updated_at = profile.available_cash_updated_at
    if updated_at is not None and updated_at.tzinfo is None:
        updated_at = updated_at.replace(tzinfo=timezone.utc)

    return CashProfileResponse(
        available_cash=profile.available_cash,
        available_cash_updated_at=updated_at,
        is_estimate=False,
    )


@router.get("/cash", response_model=CashProfileResponse)
def get_cash_profile(
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    profile = db.query(MerchantProfile).filter(MerchantProfile.user_id == current_user.id).first()
    return _response(profile)


@router.put("/cash", response_model=CashProfileResponse)
def update_cash_profile(
    data: CashProfileUpdate,
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    profile = db.query(MerchantProfile).filter(MerchantProfile.user_id == current_user.id).first()
    if profile is None:
        profile = MerchantProfile(user_id=current_user.id)
        db.add(profile)

    profile.available_cash = data.available_cash
    profile.available_cash_updated_at = (
        datetime.now(timezone.utc) if data.available_cash is not None else None
    )
    db.commit()
    db.refresh(profile)
    return _response(profile)
