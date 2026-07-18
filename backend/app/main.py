"""FastAPI application entry point."""
import sys
import os
# Ensure the app package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.database import engine
from models.base import Base

app = FastAPI(title="商资通")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
app.include_router(auth_router)
app.include_router(cards_router)
app.include_router(upload_router)
app.include_router(forecast_router)
app.include_router(calendar_router)
app.include_router(alerts_router)
app.include_router(recommend_router)
app.include_router(schedule_router)
app.include_router(stoploss_router)


@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
