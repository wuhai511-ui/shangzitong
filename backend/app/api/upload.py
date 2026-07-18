"""Upload API routes — file preview and confirm import."""
import io
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from core.database import SessionLocal
from schemas.auth import UserInfo
from schemas.datasource import UploadConfirmRequest
from ingest.upload_ingest import UploadIngest
from models.datasource import DataSource, Settlement
from api.auth import get_current_user_dependency
from decimal import Decimal

router = APIRouter(prefix="/api/v1/ingest/upload", tags=["upload"])

_preview_store: dict = {}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/preview", response_model=None)
async def upload_preview(
    file: UploadFile,
    current_user: UserInfo = Depends(get_current_user_dependency),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_content = await file.read()
    ingest = UploadIngest()
    result = ingest.parse_upload(file_content, file.filename)

    if result.errors:
        raise HTTPException(status_code=400, detail="; ".join(result.errors))

    store_key = str(current_user.id)
    _preview_store[store_key] = {
        "filename": file.filename,
        "headers": result.headers,
        "rows": result.rows,
        "total_rows": result.total_rows,
    }

    return {
        "mappings": result.mappings,
        "preview_rows": result.rows[:10],
        "total_rows": result.total_rows,
    }


@router.post("/confirm", response_model=None)
async def upload_confirm(
    body: UploadConfirmRequest,
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    store_key = str(current_user.id)
    stored = _preview_store.pop(store_key, None)

    if stored is None:
        raise HTTPException(status_code=400, detail="No preview data found")

    # Create DataSource
    ds = DataSource(
        user_id=current_user.id,
        source_type="upload",
        provider=body.provider,
        label=stored.get("filename", "upload"),
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    # Actually insert settlements from preview data
    imported = 0
    mappings = body.mappings
    date_col = mappings.get("date_column", "date")
    amount_col = mappings.get("amount_column", "amount")

    for row in stored["rows"]:
        try:
            settle_date = datetime.strptime(
                str(row.get(date_col, "")), mappings.get("date_format", "%Y-%m-%d")
            ).date()
            amount = Decimal(str(row.get(amount_col, 0)).replace(",", "").replace("¥", ""))
        except (ValueError, KeyError):
            continue

        # Check duplicate
        existing = db.query(Settlement).filter(
            Settlement.source_id == ds.id,
            Settlement.settle_date == settle_date,
            Settlement.amount == amount,
            Settlement.user_id == current_user.id,
        ).first()
        if existing:
            continue

        s = Settlement(
            source_id=ds.id,
            user_id=current_user.id,
            settle_date=settle_date,
            amount=amount,
            provider=body.provider,
            batch_hash=stored["filename"],
        )
        db.add(s)
        imported += 1

    db.commit()
    return {"imported": imported}
