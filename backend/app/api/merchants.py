from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.auth_context import UserContext, get_db, get_user_context
from schemas.merchant import (
    MerchantCreate,
    MerchantDetailResponse,
    MerchantOnboardingAppResponse,
    MerchantResponse,
)
from services.merchant_service import MerchantService
from models.merchant_onboarding import OnboardingStatus

router = APIRouter(prefix="/api/v1/merchants", tags=["merchants"])


@router.post("", response_model=MerchantDetailResponse, status_code=201)
def create_merchant(
    data: MerchantCreate,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    merchant = MerchantService.create_merchant_with_onboarding(db, ctx, data)
    return _to_detail(merchant)


@router.get("", response_model=list[MerchantResponse])
def list_merchants(
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    merchants = MerchantService.list_by_agency(db, ctx)
    return [_to_response(m) for m in merchants]


@router.get("/{merchant_id}", response_model=MerchantDetailResponse)
def get_merchant(
    merchant_id: int,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    merchant = MerchantService.get_by_id(db, ctx, merchant_id)
    return _to_detail(merchant)


@router.post("/{merchant_id}/toggle-auto-swipe", response_model=MerchantResponse)
def toggle_auto_swipe(
    merchant_id: int,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    merchant = MerchantService.toggle_auto_swipe(db, ctx, merchant_id)
    return _to_response(merchant)


def _to_response(merchant) -> MerchantResponse:
    return MerchantResponse(
        id=merchant.id,
        agency_id=merchant.agency_id,
        user_id=merchant.user_id,
        name=merchant.name,
        phone=merchant.phone,
        business_type=merchant.business_type,
        is_micro=merchant.is_micro,
        auto_swipe_enabled=merchant.auto_swipe_enabled,
        created_at=merchant.created_at,
        updated_at=merchant.updated_at,
    )


def _to_app_response(app) -> MerchantOnboardingAppResponse:
    return MerchantOnboardingAppResponse(
        id=app.id,
        agency_id=app.agency_id,
        merchant_id=app.merchant_id,
        agency_payment_channel_id=app.agency_payment_channel_id,
        provider=app.provider if isinstance(app.provider, str) else app.provider.value,
        provider_application_id=app.provider_application_id,
        external_merchant_no=app.external_merchant_no,
        status=app.status.value if hasattr(app.status, "value") else app.status,
        is_simulated=app.is_simulated,
        request_snapshot=app.request_snapshot,
        response_snapshot=app.response_snapshot,
        submitted_at=app.submitted_at,
        approved_at=app.approved_at,
        rejected_at=app.rejected_at,
        created_at=app.created_at,
        updated_at=app.updated_at,
    )


def _to_detail(merchant) -> MerchantDetailResponse:
    resp = _to_response(merchant)
    apps = []
    if hasattr(merchant, "onboarding_applications"):
        apps = [_to_app_response(a) for a in merchant.onboarding_applications]
    return MerchantDetailResponse(
        **resp.model_dump(),
        onboarding_applications=apps,
    )
