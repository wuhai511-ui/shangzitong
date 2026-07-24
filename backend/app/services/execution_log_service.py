import json
from sqlalchemy.orm import Session
from models.auto_swipe_execution_log import AutoSwipeExecutionLog


class ExecutionLogService:
    @staticmethod
    def log(db: Session, transaction_id: int | None, agency_id: int, event_type: str, event_data: dict | None = None, severity: str = "info"):
        log_entry = AutoSwipeExecutionLog(
            transaction_id=transaction_id,
            agency_id=agency_id,
            event_type=event_type,
            event_data=json.dumps(event_data, default=str) if event_data else None,
            severity=severity,
        )
        db.add(log_entry)
        db.commit()
