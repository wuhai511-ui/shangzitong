"""Upload API routes for bounded preview and one-time confirmed imports."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from api.auth import get_current_user_dependency
from core.config import settings
from core.database import SessionLocal
from ingest.upload_ingest import UploadIngest
from models.datasource import DataSource, Settlement
from schemas.auth import UserInfo
from schemas.datasource import UploadConfirmRequest

router = APIRouter(prefix="/api/v1/ingest/upload", tags=["upload"])

_preview_store: dict[str, dict] = {}
_SUPPORTED_CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030")
_NO_PREVIEW_DETAIL = "No preview data found"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _validate_file_content(filename: str, content: bytes) -> str | None:
    suffix = Path(filename).suffix.lower()
    if suffix == ".xlsx":
        if not content.startswith(b"PK"):
            raise HTTPException(status_code=400, detail="Invalid XLSX file")
        return None
    if suffix != ".csv":
        raise HTTPException(status_code=400, detail="Unsupported file type")
    if b"\x00" in content:
        raise HTTPException(status_code=400, detail="Invalid CSV file")

    for encoding in _SUPPORTED_CSV_ENCODINGS:
        try:
            content.decode(encoding)
            return encoding
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="Unsupported CSV encoding")


def _take_preview(preview_id: str | None, user_id: int) -> dict:
    now = datetime.now(timezone.utc)

    if preview_id is not None:
        stored = _preview_store.get(preview_id)
        if stored is None:
            raise HTTPException(status_code=400, detail=_NO_PREVIEW_DETAIL)
        if stored["user_id"] != user_id:
            raise HTTPException(status_code=404, detail=_NO_PREVIEW_DETAIL)
        if stored["expires_at"] <= now:
            _preview_store.pop(preview_id, None)
            raise HTTPException(status_code=400, detail=_NO_PREVIEW_DETAIL)

        stored = _preview_store.pop(preview_id, None)
        if stored is None:
            raise HTTPException(status_code=400, detail=_NO_PREVIEW_DETAIL)
        return stored

    candidates: list[tuple[str, dict]] = []
    for stored_id, stored in list(_preview_store.items()):
        if stored["user_id"] != user_id:
            continue
        if stored["expires_at"] <= now:
            _preview_store.pop(stored_id, None)
            continue
        candidates.append((stored_id, stored))

    if not candidates:
        raise HTTPException(status_code=400, detail=_NO_PREVIEW_DETAIL)

    selected_id, _ = max(candidates, key=lambda item: item[1]["created_at"])
    selected = _preview_store.pop(selected_id, None)
    if selected is None:
        raise HTTPException(status_code=400, detail=_NO_PREVIEW_DETAIL)
    return selected


@router.post("/preview", response_model=None)
async def upload_preview(
    file: UploadFile,
    current_user: UserInfo = Depends(get_current_user_dependency),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    safe_name = Path(file.filename.replace("\\", "/")).name
    file_content = await file.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(file_content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds 10 MiB limit")

    encoding = _validate_file_content(safe_name, file_content)
    ingest = UploadIngest()
    parse_options = {"encoding": encoding} if encoding else {}
    result = ingest.parse_upload(file_content, safe_name, **parse_options)

    if result.errors:
        raise HTTPException(status_code=400, detail="; ".join(result.errors))

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=settings.UPLOAD_PREVIEW_TTL_SECONDS)
    preview_id = uuid4().hex
    _preview_store[preview_id] = {
        "user_id": current_user.id,
        "filename": safe_name,
        "headers": result.headers,
        "rows": result.rows,
        "total_rows": result.total_rows,
        "created_at": now,
        "expires_at": expires_at,
    }

    return {
        "preview_id": preview_id,
        "mappings": result.mappings,
        "preview_rows": result.rows[:10],
        "total_rows": result.total_rows,
        "expires_at": expires_at,
    }


@router.post("/confirm", response_model=None)
async def upload_confirm(
    body: UploadConfirmRequest,
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    stored = _take_preview(body.preview_id, current_user.id)

    ds = DataSource(
        user_id=current_user.id,
        source_type="upload",
        provider=body.provider,
        label=stored.get("filename", "upload"),
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

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

        existing = db.query(Settlement).filter(
            Settlement.source_id == ds.id,
            Settlement.settle_date == settle_date,
            Settlement.amount == amount,
            Settlement.user_id == current_user.id,
        ).first()
        if existing:
            continue

        settlement = Settlement(
            source_id=ds.id,
            user_id=current_user.id,
            settle_date=settle_date,
            amount=amount,
            provider=body.provider,
            batch_hash=stored["filename"],
        )
        db.add(settlement)
        imported += 1

    db.commit()
    return {"imported": imported}
