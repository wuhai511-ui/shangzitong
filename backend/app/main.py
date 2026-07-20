"""FastAPI application entry point."""
import sys
import os
# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import engine
from models.base import Base

# Import all models so they register with Base.metadata before create_all
import models.user         # noqa: F401
import models.card         # noqa: F401
import models.datasource   # noqa: F401
import models.sftp_config  # noqa: F401
import models.email_config # noqa: F401
import models.bank         # noqa: F401

# Create tables at module level (SQLite, instant)
Base.metadata.create_all(bind=engine)

# Seed bank dictionary
from core.database import SessionLocal
from models.bank import Bank, DEFAULT_BANKS
db = SessionLocal()
try:
    if db.query(Bank).count() == 0:
        for i, (name, code) in enumerate(DEFAULT_BANKS):
            db.add(Bank(name=name, code=code, sort_order=i))
        db.commit()
finally:
    db.close()

app = FastAPI(title="商资通")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://47.253.226.91", "http://localhost", "http://127.0.0.1"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
from api.auth import router as auth_router
from api.cards import router as cards_router
from api.upload import router as upload_router
from api.forecast import router as forecast_router
from api.calendar import router as calendar_router
from api.alerts import router as alerts_router
from api.recommend import router as recommend_router
from api.schedule import router as schedule_router
from api.stoploss import router as stoploss_router
from api.sftp import router as sftp_router
from api.email_ingest import router as email_ingest_router
from api.report import router as report_router
from api.banks import router as banks_router
app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(upload_router)
app.include_router(forecast_router)
app.include_router(calendar_router)
app.include_router(alerts_router)
app.include_router(recommend_router)
app.include_router(schedule_router)
app.include_router(stoploss_router)
app.include_router(sftp_router)
app.include_router(email_ingest_router)
app.include_router(report_router)
app.include_router(banks_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}
