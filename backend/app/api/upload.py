"""Upload API routes for bounded preview and one-time confirmed imports."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import io
from pathlib import Path, PureWindowsPath
import stat
from uuid import uuid4
import zipfile

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from api.auth import get_current_user_dependency
from core.config import settings
from core.database import SessionLocal
from ingest.upload_ingest import UploadIngest
from models.datasource import DataSource, Settlement
from schemas.auth import UserInfo
from schemas.datasource import UploadConfirmRequest, UploadPreviewResponse

router = APIRouter(prefix="/api/v1/ingest/upload", tags=["upload"])

_preview_store: dict[str, dict] = {}
_SUPPORTED_CSV_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030")
_NO_PREVIEW_DETAIL = "No preview data found"

MAX_PREVIEWS_PER_USER = 5
MAX_PREVIEWS_TOTAL = 100
MAX_XLSX_MEMBERS = 1000
MAX_PREVIEW_BYTES_PER_USER = 20 * 1024 * 1024
MAX_PREVIEW_BYTES_TOTAL = 50 * 1024 * 1024
MAX_XLSX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_XLSX_COMPRESSION_RATIO = 100


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _invalid_xlsx() -> HTTPException:
    return HTTPException(status_code=400, detail="Invalid XLSX file")


def _validate_xlsx_content(content: bytes) -> None:
    archive_buffer = io.BytesIO(content)
    if not zipfile.is_zipfile(archive_buffer):
        raise _invalid_xlsx()

    archive_buffer.seek(0)
    try:
        with zipfile.ZipFile(archive_buffer) as archive:
            members = archive.infolist()
            if not members or len(members) > MAX_XLSX_MEMBERS:
                raise _invalid_xlsx()

            total_compressed = 0
            total_uncompressed = 0
            for member in members:
                name = member.filename
                if not name or "\x00" in name or "\\" in name:
                    raise _invalid_xlsx()

                path_name = name[:-1] if member.is_dir() else name
                parts = path_name.split("/")
                if (
                    not path_name
                    or name.startswith("/")
                    or PureWindowsPath(path_name).is_absolute()
                    or bool(PureWindowsPath(path_name).drive)
                    or any(part in {"", ".", ".."} for part in parts)
                ):
                    raise _invalid_xlsx()

                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode) or member.flag_bits & 0x1:
                    raise _invalid_xlsx()
                if member.is_dir():
                    continue

                total_compressed += member.compress_size
                total_uncompressed += member.file_size
                if total_uncompressed > MAX_XLSX_UNCOMPRESSED_BYTES:
                    raise _invalid_xlsx()

            if total_uncompressed and total_compressed == 0:
                raise _invalid_xlsx()
            if (
                total_uncompressed
                and total_uncompressed / total_compressed > MAX_XLSX_COMPRESSION_RATIO
            ):
                raise _invalid_xlsx()
            if archive.testzip() is not None:
                raise _invalid_xlsx()
    except HTTPException:
        raise
    except (OSError, RuntimeError, ValueError, zipfile.BadZipFile):
        raise _invalid_xlsx()


def _validate_file_content(filename: str, content: bytes) -> str | None:
    suffix = Path(filename).suffix.lower()
    if suffix == ".xlsx":
        if not content.startswith(b"PK"):
            raise _invalid_xlsx()
        _validate_xlsx_content(content)
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


def _sweep_expired_previews(now: datetime | None = None) -> None:
    cutoff = now or datetime.now(timezone.utc)
    for stored_id, stored in list(_preview_store.items()):
        if stored["expires_at"] <= cutoff:
            _preview_store.pop(stored_id, None)


def _enforce_preview_capacity(user_id: int) -> None:
    if len(_preview_store) >= MAX_PREVIEWS_TOTAL:
        raise HTTPException(status_code=429, detail="Too many active upload previews")
    user_previews = sum(
        stored["user_id"] == user_id for stored in _preview_store.values()
    )
    if user_previews >= MAX_PREVIEWS_PER_USER:
        raise HTTPException(status_code=429, detail="Too many active upload previews")


def _enforce_preview_byte_budget(user_id: int, content_size: int) -> None:
    user_bytes = sum(
        len(stored["file_content"])
        for stored in _preview_store.values()
        if stored["user_id"] == user_id
    )
    if user_bytes + content_size > MAX_PREVIEW_BYTES_PER_USER:
        raise HTTPException(status_code=429, detail="Upload preview byte budget exceeded")
    total_bytes = sum(
        len(stored["file_content"]) for stored in _preview_store.values()
    )
    if total_bytes + content_size > MAX_PREVIEW_BYTES_TOTAL:
        raise HTTPException(status_code=429, detail="Upload preview byte budget exceeded")


def _take_preview(preview_id: str | None, user_id: int) -> dict:
    now = datetime.now(timezone.utc)
    _sweep_expired_previews(now)

    if preview_id is not None:
        stored = _preview_store.get(preview_id)
        if stored is None:
            raise HTTPException(status_code=400, detail=_NO_PREVIEW_DETAIL)
        if stored["user_id"] != user_id:
            raise HTTPException(status_code=404, detail=_NO_PREVIEW_DETAIL)

        stored = _preview_store.pop(preview_id, None)
        if stored is None:
            raise HTTPException(status_code=400, detail=_NO_PREVIEW_DETAIL)
        return stored

    candidates = [
        (stored_id, stored)
        for stored_id, stored in _preview_store.items()
        if stored["user_id"] == user_id
    ]
    if not candidates:
        raise HTTPException(status_code=400, detail=_NO_PREVIEW_DETAIL)

    selected_id, _ = max(candidates, key=lambda item: item[1]["created_at"])
    selected = _preview_store.pop(selected_id, None)
    if selected is None:
        raise HTTPException(status_code=400, detail=_NO_PREVIEW_DETAIL)
    return selected


@router.post("/preview", response_model=UploadPreviewResponse)
async def upload_preview(
    file: UploadFile,
    current_user: UserInfo = Depends(get_current_user_dependency),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    _sweep_expired_previews()
    _enforce_preview_capacity(current_user.id)

    safe_name = Path(file.filename.replace("\\", "/")).name
    file_content = await file.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(file_content) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload exceeds 10 MiB limit")

    encoding = _validate_file_content(safe_name, file_content)
    ingest = UploadIngest()
    parse_options = {"encoding": encoding} if encoding else {}
    result = ingest.parse_upload(
        file_content,
        safe_name,
        max_rows=settings.UPLOAD_MAX_ROWS,
        max_columns=settings.UPLOAD_MAX_COLUMNS,
        max_cells=settings.UPLOAD_MAX_CELLS,
        **parse_options,
    )

    if result.errors:
        raise HTTPException(status_code=400, detail="; ".join(result.errors))

    now = datetime.now(timezone.utc)
    _sweep_expired_previews(now)
    _enforce_preview_capacity(current_user.id)
    _enforce_preview_byte_budget(current_user.id, len(file_content))

    expires_at = now + timedelta(seconds=settings.UPLOAD_PREVIEW_TTL_SECONDS)
    preview_id = uuid4().hex
    while preview_id in _preview_store:
        preview_id = uuid4().hex
    _preview_store[preview_id] = {
        "user_id": current_user.id,
        "filename": safe_name,
        "file_content": file_content,
        "encoding": encoding,
        "headers": result.headers,
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

    ingest = UploadIngest()
    confirm_parse_options = (
        {"encoding": stored["encoding"]} if stored.get("encoding") else {}
    )
    result = ingest.parse_upload(
        stored["file_content"],
        stored.get("filename", "upload"),
        max_rows=settings.UPLOAD_MAX_ROWS,
        max_columns=settings.UPLOAD_MAX_COLUMNS,
        max_cells=settings.UPLOAD_MAX_CELLS,
        **confirm_parse_options,
    )
    if result.errors:
        raise HTTPException(status_code=400, detail="; ".join(result.errors))

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

    for row in result.rows:
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
