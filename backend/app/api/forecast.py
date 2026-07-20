"""Settlement forecast API."""
from fastapi import APIRouter, Depends
from core.database import SessionLocal
from schemas.auth import UserInfo
from api.auth import get_current_user_dependency
from algorithm.settlement import build_forecast
from models.datasource import Settlement
from services.cashflow_service import aggregate_settlement_history
from datetime import date, timedelta

router = APIRouter(prefix="/api/v1/settlements", tags=["settlements"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/forecast", response_model=None)
def get_forecast(current_user: UserInfo = Depends(get_current_user_dependency),
                 db=Depends(get_db)):
    """Return 30-day settlement forecast based on historical data."""
    # Load historical settlements
    cutoff = date.today() - timedelta(days=90)
    rows = db.query(Settlement).filter(
        Settlement.user_id == current_user.id,
        Settlement.settle_date >= cutoff,
        Settlement.deleted_at.is_(None)
    ).all()

    history = aggregate_settlement_history(rows)

    # Build forecast
    forecasts = build_forecast(date.today(), history, days=30)

    return {
        "days": 30,
        "forecast": [
            {
                "date": str(f.date),
                "amount": str(f.amount),
                "confidence": f.confidence,
                "arrival": str(f.arrival),
            }
            for f in forecasts
        ],
    }
