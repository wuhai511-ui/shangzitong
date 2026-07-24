import json
from sqlalchemy.orm import Session
from models.auto_swipe_policy import AutoSwipePolicy
from core.auth_context import UserContext
from fastapi import HTTPException

DEFAULT_RETRY_STRATEGY = json.dumps({"max_retries": 3, "backoff_seconds": 60, "backoff_multiplier": 2})


class PolicyService:
    @staticmethod
    def get_or_create(db: Session, agency_id: int) -> AutoSwipePolicy:
        policy = db.query(AutoSwipePolicy).filter(AutoSwipePolicy.agency_id == agency_id).first()
        if not policy:
            policy = AutoSwipePolicy(
                agency_id=agency_id, max_parallel_transactions=3,
                retry_strategy=DEFAULT_RETRY_STRATEGY, is_active=False,
            )
            db.add(policy)
            db.commit()
            db.refresh(policy)
        return policy

    @staticmethod
    def update(db: Session, ctx: UserContext, agency_id: int, data: dict) -> AutoSwipePolicy:
        ctx.require_agent()
        policy = PolicyService.get_or_create(db, agency_id)
        for k, v in data.items():
            if hasattr(policy, k) and v is not None:
                setattr(policy, k, v)
        db.commit()
        db.refresh(policy)
        return policy
