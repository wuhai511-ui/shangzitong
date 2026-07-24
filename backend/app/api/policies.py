from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.auth_context import UserContext, get_db, get_user_context
from services.policy_service import PolicyService

router = APIRouter(prefix="/api/v1/agencies", tags=["policies"])


@router.get("/{agency_id}/auto-swipe-policy")
def get_auto_swipe_policy(
    agency_id: int,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    ctx.require_agent()
    if ctx.role == "agent_admin" and ctx.agency_id != agency_id:
        raise HTTPException(403, "Permission denied")
    policy = PolicyService.get_or_create(db, agency_id)
    return {
        "id": policy.id,
        "agency_id": policy.agency_id,
        "max_daily_per_merchant": str(policy.max_daily_per_merchant) if policy.max_daily_per_merchant else None,
        "max_single_amount": str(policy.max_single_amount) if policy.max_single_amount else None,
        "min_interest_free_days": policy.min_interest_free_days,
        "max_parallel_transactions": policy.max_parallel_transactions,
        "retry_strategy": policy.retry_strategy,
        "swipe_window_start": str(policy.swipe_window_start) if policy.swipe_window_start else None,
        "swipe_window_end": str(policy.swipe_window_end) if policy.swipe_window_end else None,
        "notification_webhook": policy.notification_webhook,
        "is_active": policy.is_active,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }


@router.patch("/{agency_id}/auto-swipe-policy")
def update_auto_swipe_policy(
    agency_id: int,
    data: dict,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    ctx.require_agent()
    if ctx.role == "agent_admin" and ctx.agency_id != agency_id:
        raise HTTPException(403, "Permission denied")
    policy = PolicyService.update(db, ctx, agency_id, data)
    return {
        "id": policy.id,
        "agency_id": policy.agency_id,
        "max_daily_per_merchant": str(policy.max_daily_per_merchant) if policy.max_daily_per_merchant else None,
        "max_single_amount": str(policy.max_single_amount) if policy.max_single_amount else None,
        "min_interest_free_days": policy.min_interest_free_days,
        "max_parallel_transactions": policy.max_parallel_transactions,
        "retry_strategy": policy.retry_strategy,
        "swipe_window_start": str(policy.swipe_window_start) if policy.swipe_window_start else None,
        "swipe_window_end": str(policy.swipe_window_end) if policy.swipe_window_end else None,
        "notification_webhook": policy.notification_webhook,
        "is_active": policy.is_active,
        "created_at": policy.created_at.isoformat() if policy.created_at else None,
        "updated_at": policy.updated_at.isoformat() if policy.updated_at else None,
    }
