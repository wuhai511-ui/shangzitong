from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.auth_context import UserContext, get_db, get_user_context
from schemas.agency import AgencyCreate, AgencyUpdate, AgencyResponse
from services.agency_service import AgencyService

router = APIRouter(prefix="/api/v1/agencies", tags=["agencies"])


@router.get("/me", response_model=AgencyResponse)
def me(
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    if ctx.role not in ("super_admin", "agent_admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Agency not found")
    if ctx.agency_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No agency assigned")
    return AgencyService.get_by_id(db, ctx, ctx.agency_id)


@router.get("", response_model=list[AgencyResponse])
def list_agencies(
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    return AgencyService.list_all(db, ctx)


@router.get("/{agency_id}", response_model=AgencyResponse)
def get_agency(
    agency_id: int,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    return AgencyService.get_by_id(db, ctx, agency_id)


@router.post("", response_model=AgencyResponse, status_code=201)
def create_agency(
    data: AgencyCreate,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    return AgencyService.create(db, ctx, data)


@router.put("/{agency_id}", response_model=AgencyResponse)
def update_agency(
    agency_id: int,
    data: AgencyUpdate,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    return AgencyService.update(db, ctx, agency_id, data)


@router.post("/{agency_id}/suspend", response_model=AgencyResponse)
def suspend_agency(
    agency_id: int,
    ctx: UserContext = Depends(get_user_context),
    db: Session = Depends(get_db),
):
    return AgencyService.suspend(db, ctx, agency_id)
