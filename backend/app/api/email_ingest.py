"""Email ingestion API routes."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from core.database import SessionLocal, get_db
from schemas.auth import UserInfo
from schemas.datasource import (
    EmailConfigureRequest,
    EmailStatusResponse,
    EmailTriggerResponse,
)
from models.datasource import DataSource
from models.email_config import EmailConfig
from ingest.email_ingest import EmailPoller
from ingest.upload_ingest import UploadIngest
from api.auth import get_current_user_dependency

router = APIRouter(prefix="/api/v1/ingest/email", tags=["email_ingest"])


@router.post("/configure", response_model=None)
def email_configure(
    body: EmailConfigureRequest,
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    config = db.query(EmailConfig).filter(
        EmailConfig.user_id == current_user.id,
    ).first()

    if config:
        config.email = body.email
        config.imap_host = body.imap_host
        config.imap_port = body.imap_port
        config.username = body.username
        config.password = body.password
        config.use_ssl = body.use_ssl
    else:
        config = EmailConfig(
            user_id=current_user.id,
            email=body.email,
            imap_host=body.imap_host,
            imap_port=body.imap_port,
            username=body.username,
            password=body.password,
            use_ssl=body.use_ssl,
        )
        db.add(config)
    db.commit()

    return {"message": "email configuration saved"}


@router.get("/status", response_model=EmailStatusResponse)
def email_status(
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    config = db.query(EmailConfig).filter(
        EmailConfig.user_id == current_user.id,
    ).first()

    if not config:
        raise HTTPException(status_code=404, detail="Email not configured")

    poller = EmailPoller(
        imap_host=config.imap_host,
        imap_port=config.imap_port,
        username=config.username,
        password=config.password,
        use_ssl=config.use_ssl,
    )
    connected, message, msg_count = poller.test_connection()

    return EmailStatusResponse(
        enabled=config.enabled,
        message=f"{message} ({msg_count} messages)" if connected else message,
        email=config.email,
        imap_host=config.imap_host,
        last_poll_at=config.last_poll_at,
    )


@router.post("/trigger", response_model=EmailTriggerResponse)
def email_trigger(
    current_user: UserInfo = Depends(get_current_user_dependency),
    db=Depends(get_db),
):
    config = db.query(EmailConfig).filter(
        EmailConfig.user_id == current_user.id,
    ).first()

    if not config:
        raise HTTPException(status_code=400, detail="Email not configured")

    ds = db.query(DataSource).filter(
        DataSource.user_id == current_user.id,
        DataSource.source_type == "email",
        DataSource.label == config.email,
    ).first()

    if not ds:
        ds = DataSource(
            user_id=current_user.id,
            source_type="email",
            provider="email",
            label=config.email,
        )
        db.add(ds)
        db.commit()
        db.refresh(ds)

    poller = EmailPoller(
        imap_host=config.imap_host,
        imap_port=config.imap_port,
        username=config.username,
        password=config.password,
        use_ssl=config.use_ssl,
    )

    ingest = UploadIngest()
    try:
        result = poller.poll(source_id=ds.id, user_id=current_user.id,
                             db_session=db, ingest=ingest)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Email poll failed: {str(e)}")

    if result.get("emails_processed", 0) > 0 or result.get("settlements_imported", 0) > 0:
        config.last_poll_at = datetime.now(timezone.utc)
        db.commit()

    return EmailTriggerResponse(
        message=f"processed {result.get('emails_processed', 0)} emails, "
                f"imported {result.get('settlements_imported', 0)} settlements",
        emails_processed=result.get("emails_processed", 0),
        settlements_imported=result.get("settlements_imported", 0),
        errors=result.get("errors", []),
    )
