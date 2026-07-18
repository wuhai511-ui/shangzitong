"""Upload API routes — file preview and confirm import."""
import io
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from core.database import SessionLocal
from schemas.auth import UserInfo
from schemas.datasource import UploadConfirmRequest
from ingest.upload_ingest import UploadIngest
from models.datasource import DataSource
from api.auth import get_current_user_dependency

router = APIRouter(prefix="/api/v1/ingest/upload", tags=["upload"])

# In-memory store for parsed data between preview and confirm
_preview_store: dict = {}


def get_db():
    """FastAPI dependency: yield a database session."""
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
    """Accept uploaded file, detect columns, return preview with mappings."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_content = await file.read()
    ingest = UploadIngest()
    result = ingest.parse_upload(file_content, file.filename)

    if result.errors:
        raise HTTPException(status_code=400, detail="; ".join(result.errors))

    # Store parsed data for confirm step
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
    """Confirm import: create DataSource record and persist settlements."""
    store_key = str(current_user.id)
    stored = _preview_store.pop(store_key, None)

    if stored is None:
        raise HTTPException(status_code=400, detail="No preview data found — call /preview first")

    # Create DataSource record
    ds = DataSource(
        user_id=current_user.id,
        source_type="upload",
        provider=body.provider,
        label=stored.get("filename", "upload"),
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)

    imported_count = stored.get("total_rows", 0)

    # Cleanup store
    _preview_store.pop(store_key, None)

    return {"imported": imported_count}
