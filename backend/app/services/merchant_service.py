from sqlalchemy.orm import Session, joinedload

from fastapi import HTTPException

from models.merchant import Merchant
from models.merchant_onboarding import MerchantOnboardingApplication, OnboardingStatus
from schemas.merchant import MerchantCreate
from core.auth_context import UserContext


class MerchantService:
    @staticmethod
    def create_merchant_with_onboarding(
        db: Session, ctx: UserContext, data: MerchantCreate
    ) -> Merchant:
        if ctx.role not in ("super_admin", "agent_admin"):
            raise HTTPException(403, "Permission denied")
        if ctx.role == "agent_admin" and ctx.agency_id is None:
            raise HTTPException(403, "No agency assigned")

        agency_id = ctx.agency_id if ctx.role == "agent_admin" else 0

        merchant = Merchant(
            agency_id=agency_id,
            name=data.name,
            phone=data.phone,
            business_type=data.business_type,
            is_micro=data.is_micro,
            auto_swipe_enabled=False,
        )
        db.add(merchant)
        db.flush()

        application = MerchantOnboardingApplication(
            agency_id=agency_id,
            merchant_id=merchant.id,
            agency_payment_channel_id=data.channel_id,
            provider="",
            status=OnboardingStatus.pending,
            is_simulated=False,
        )
        db.add(application)
        db.commit()
        db.refresh(merchant)
        return merchant

    @staticmethod
    def list_by_agency(db: Session, ctx: UserContext, agency_id: int) -> list[Merchant]:
        if ctx.role not in ("super_admin", "agent_admin"):
            raise HTTPException(403, "Permission denied")
        if ctx.role == "agent_admin" and ctx.agency_id != agency_id:
            raise HTTPException(403, "Permission denied")
        return db.query(Merchant).filter(
            Merchant.agency_id == agency_id,
            Merchant.deleted_at.is_(None),
        ).all()

    @staticmethod
    def get_by_id(db: Session, ctx: UserContext, merchant_id: int) -> Merchant:
        query = db.query(Merchant).options(
            joinedload(Merchant.onboarding_applications)
        ).filter(
            Merchant.id == merchant_id,
            Merchant.deleted_at.is_(None),
        )
        if ctx.role == "agent_admin":
            query = query.filter(Merchant.agency_id == ctx.agency_id)
        elif ctx.role == "merchant":
            query = query.filter(Merchant.user_id == ctx.user_id)

        merchant = query.first()
        if not merchant:
            raise HTTPException(404, "Merchant not found")
        return merchant

    @staticmethod
    def toggle_auto_swipe(db: Session, ctx: UserContext, merchant_id: int) -> Merchant:
        if ctx.role not in ("super_admin", "agent_admin"):
            raise HTTPException(403, "Permission denied")

        merchant = db.query(Merchant).filter(
            Merchant.id == merchant_id,
            Merchant.deleted_at.is_(None),
        ).first()
        if not merchant:
            raise HTTPException(404, "Merchant not found")
        if ctx.role == "agent_admin" and ctx.agency_id != merchant.agency_id:
            raise HTTPException(403, "Permission denied")

        merchant.auto_swipe_enabled = not merchant.auto_swipe_enabled
        db.commit()
        db.refresh(merchant)
        return merchant
