from sqlalchemy.orm import Session

from fastapi import HTTPException

from models.agency_payment_channel import AgencyPaymentChannel
from schemas.channel import ChannelCreate
from core.auth_context import UserContext
from core.crypto import encrypt_field, mask_value


class ChannelService:
    @staticmethod
    def create(db: Session, ctx: UserContext, data: ChannelCreate) -> AgencyPaymentChannel:
        if ctx.role not in ("super_admin", "agent_admin"):
            raise HTTPException(403, "Permission denied")
        if ctx.role == "agent_admin" and ctx.agency_id is None:
            raise HTTPException(403, "No agency assigned")

        channel = AgencyPaymentChannel(
            agency_id=ctx.agency_id if ctx.role == "agent_admin" else 0,
            provider=data.provider,
            org_no=data.org_no,
            api_key_cipher=encrypt_field(data.api_key),
            api_secret_cipher=encrypt_field(data.api_secret),
        )
        db.add(channel)
        db.commit()
        db.refresh(channel)
        return channel

    @staticmethod
    def list_by_agency(db: Session, ctx: UserContext, agency_id: int) -> list[AgencyPaymentChannel]:
        if ctx.role not in ("super_admin", "agent_admin"):
            raise HTTPException(403, "Permission denied")
        if ctx.role == "agent_admin" and ctx.agency_id != agency_id:
            raise HTTPException(403, "Permission denied")
        return db.query(AgencyPaymentChannel).filter(
            AgencyPaymentChannel.agency_id == agency_id
        ).all()

    @staticmethod
    def delete(db: Session, ctx: UserContext, channel_id: int):
        if ctx.role not in ("super_admin", "agent_admin"):
            raise HTTPException(403, "Permission denied")
        channel = db.query(AgencyPaymentChannel).filter(
            AgencyPaymentChannel.id == channel_id
        ).first()
        if not channel:
            raise HTTPException(404, "Channel not found")
        if ctx.role == "agent_admin" and ctx.agency_id != channel.agency_id:
            raise HTTPException(403, "Permission denied")
        db.delete(channel)
        db.commit()
