from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from core.auth_context import UserContext, get_db, get_user_context
from schemas.channel import ChannelCreate, ChannelResponse
from services.channel_service import ChannelService
from core.crypto import mask_value

router = APIRouter(prefix="/api/v1/payment-channels", tags=["payment-channels"])


@router.post("", response_model=ChannelResponse, status_code=201)
def create_channel(
    data: ChannelCreate,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    channel = ChannelService.create(db, ctx, data)
    return _to_response(channel)


@router.get("", response_model=list[ChannelResponse])
def list_channels(
    agency_id: int,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    channels = ChannelService.list_by_agency(db, ctx, agency_id)
    return [_to_response(c) for c in channels]


@router.delete("/{channel_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_channel(
    channel_id: int,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    ChannelService.delete(db, ctx, channel_id)


def _to_response(channel) -> ChannelResponse:
    return ChannelResponse(
        id=channel.id,
        agency_id=channel.agency_id,
        provider=channel.provider.value if hasattr(channel.provider, "value") else channel.provider,
        org_no=channel.org_no,
        api_key_masked=mask_value(channel.api_key_cipher, 4),
        api_secret_masked=mask_value(channel.api_secret_cipher, 4),
        key_version=channel.key_version,
        status=channel.status,
        created_at=channel.created_at,
        updated_at=channel.updated_at,
    )
