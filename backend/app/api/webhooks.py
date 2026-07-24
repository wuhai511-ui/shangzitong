import json
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from core.database import get_db
from models.payment_webhook_event import PaymentWebhookEvent
from models.agency_payment_channel import AgencyPaymentChannel

router = APIRouter(prefix="/webhooks/payment", tags=["webhooks"])


@router.post("/{provider}")
async def receive_webhook(provider: str, request: Request, db: Session = Depends(get_db)):
    raw_body = await request.body()
    body_text = raw_body.decode("utf-8")
    try:
        body_json = json.loads(body_text)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON body")

    provider_event_id = body_json.get("event_id") or body_json.get("application_id") or "unknown"
    provider_event_type = body_json.get("event_type", "unknown")

    channel = db.query(AgencyPaymentChannel).filter(AgencyPaymentChannel.provider == provider).first()
    if not channel:
        raise HTTPException(404, f"No channel found for provider: {provider}")

    existing = db.query(PaymentWebhookEvent).filter(PaymentWebhookEvent.provider_event_id == str(provider_event_id)).first()
    if existing:
        return {"status": "duplicate", "event_id": provider_event_id}

    event = PaymentWebhookEvent(
        agency_id=channel.agency_id, channel_id=channel.id,
        provider=provider, provider_event_type=provider_event_type,
        provider_event_id=str(provider_event_id), raw_body=body_text,
        status="received",
    )
    db.add(event)
    db.commit()
    return {"status": "received", "event_id": provider_event_id}
