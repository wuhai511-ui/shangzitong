"""FastAPI application entry point."""
from contextlib import asynccontextmanager
import os
import sys

# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all models so they register with Base.metadata before startup.
import models.user                # noqa: F401
import models.card                # noqa: F401
import models.datasource          # noqa: F401
import models.sftp_config         # noqa: F401
import models.email_config        # noqa: F401
import models.bank                # noqa: F401
import models.merchant_profile    # noqa: F401
import models.manual_settlement   # noqa: F401
import models.agency              # noqa: F401
import models.agency_payment_channel  # noqa: F401
import models.merchant            # noqa: F401
import models.merchant_onboarding # noqa: F401
import models.onboarding_invite   # noqa: F401
import models.onboarding_session  # noqa: F401

from core.bootstrap import initialize_database
from core.config import settings
from core.csrf import CSRFMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


app = FastAPI(title="商资通", lifespan=lifespan)

app.add_middleware(CSRFMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.H5_ALLOWED_ORIGINS.split(","),
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
from api.report import router as report_router
from api.banks import router as banks_router
from api.profile import router as profile_router
from api.agencies import router as agencies_router
from api.cashflow import router as cashflow_router
from api.channels import router as channels_router
from api.manual_settlement import router as manual_settlement_router

if settings.ENABLE_SFTP_INGEST:
    from api.sftp import router as sftp_router
if settings.ENABLE_EMAIL_INGEST:
    from api.email_ingest import router as email_ingest_router

app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(upload_router)
app.include_router(forecast_router)
app.include_router(calendar_router)
app.include_router(alerts_router)
app.include_router(recommend_router)
app.include_router(schedule_router)
app.include_router(stoploss_router)
if settings.ENABLE_SFTP_INGEST:
    app.include_router(sftp_router)
if settings.ENABLE_EMAIL_INGEST:
    app.include_router(email_ingest_router)
app.include_router(report_router)
app.include_router(banks_router)
app.include_router(profile_router)
app.include_router(agencies_router)
app.include_router(cashflow_router)
app.include_router(channels_router)
app.include_router(manual_settlement_router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
