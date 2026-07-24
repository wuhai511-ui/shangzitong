import json
from sqlalchemy.orm import Session
from models.sensitive_data_audit import SensitiveDataAudit


class SensitiveDataAuditService:
    @staticmethod
    def log(db: Session, *, actor_user_id: int, action: str, resource_type: str, resource_id: int, agency_id: int, reason: str | None = None):
        entry = SensitiveDataAudit(
            actor_user_id=actor_user_id, action=action,
            resource_type=resource_type, resource_id=resource_id,
            agency_id=agency_id, reason=reason,
        )
        db.add(entry)
        db.commit()
