"""SFTP ingestion API routes."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from core.database import SessionLocal, get_db
from schemas.auth import UserInfo
from schemas.datasource import (
    SftpConfigureRequest,
    SftpStatusResponse,
    SftpTriggerResponse,
)
from models.datasource import DataSource
from models.sftp_config import SftpConfig
from ingest.sftp_ingest import SftpPoller
from ingest.upload_ingest import UploadIngest
from api.auth import get_current_user_dependency

router = APIRouter(prefix="/api/v1/ingest/sftp", tags=["sftp"])


@router.post("/configure", response_model=None)
def sftp_configure(
    body: SftpConfigureRequest,
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    config = db.query(SftpConfig).filter(
        SftpConfig.user_id == current_user.id,
    ).first()

    if config:
        config.host = body.host
        config.port = body.port
        config.username = body.username
        config.password = body.password
        config.remote_path = body.remote_path
        config.file_pattern = body.file_pattern
    else:
        config = SftpConfig(
            user_id=current_user.id,
            host=body.host,
            port=body.port,
            username=body.username,
            password=body.password,
            remote_path=body.remote_path,
            file_pattern=body.file_pattern,
        )
        db.add(config)
    db.commit()

    return {"message": "sftp configuration saved"}


@router.get("/status", response_model=SftpStatusResponse)
def sftp_status(
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    config = db.query(SftpConfig).filter(
        SftpConfig.user_id == current_user.id,
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="SFTP not configured")

    poller = SftpPoller(
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password,
        remote_path=config.remote_path,
        file_pattern=config.file_pattern,
    )
    connected, message, files = poller.test_connection()

    return SftpStatusResponse(
        connected=connected,
        message=message,
        host=config.host,
        remote_path=config.remote_path,
        file_pattern=config.file_pattern,
        files_found=len(files),
        last_poll_at=config.last_poll_at,
    )


@router.post("/trigger", response_model=SftpTriggerResponse)
def sftp_trigger(
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    config = db.query(SftpConfig).filter(
        SftpConfig.user_id == current_user.id,
    ).first()

    if not config:
        raise HTTPException(status_code=400, detail="SFTP not configured")

    ds = db.query(DataSource).filter(
        DataSource.user_id == current_user.id,
        DataSource.source_type == "sftp",
        DataSource.label == f"sftp://{config.host}:{config.port}{config.remote_path}",
    ).first()

    if not ds:
        ds = DataSource(
            user_id=current_user.id,
            source_type="sftp",
            provider="sftp",
            label=f"sftp://{config.host}:{config.port}{config.remote_path}",
        )
        db.add(ds)
        db.commit()
        db.refresh(ds)

    poller = SftpPoller(
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password,
        remote_path=config.remote_path,
        file_pattern=config.file_pattern,
    )

    ingest = UploadIngest()
    try:
        result = poller.poll(source_id=ds.id, user_id=current_user.id,
                             db_session=db, ingest=ingest)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"SFTP poll failed: {str(e)}")

    if result.get("files_processed", 0) > 0 or result.get("settlements_imported", 0) > 0:
        config.last_poll_at = datetime.now(timezone.utc)
        db.commit()

    return SftpTriggerResponse(
        message=f"processed {result.get('files_processed', 0)} files, "
                f"imported {result.get('settlements_imported', 0)} settlements",
        files_processed=result.get("files_processed", 0),
        settlements_imported=result.get("settlements_imported", 0),
        errors=result.get("errors", []),
    )
