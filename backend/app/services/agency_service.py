from sqlalchemy.orm import Session

from fastapi import HTTPException

from models.agency import Agency
from schemas.agency import AgencyCreate, AgencyUpdate
from core.auth_context import UserContext


class AgencyService:
    @staticmethod
    def create(db: Session, ctx: UserContext, data: AgencyCreate) -> Agency:
        if ctx.role != "super_admin":
            raise HTTPException(403, "Only super_admin can create agencies")
        agency = Agency(**data.model_dump())
        db.add(agency)
        db.commit()
        db.refresh(agency)
        return agency

    @staticmethod
    def get_by_id(db: Session, ctx: UserContext, agency_id: int) -> Agency:
        agency = db.query(Agency).filter(Agency.id == agency_id).first()
        if not agency:
            raise HTTPException(404, "Agency not found")
        if ctx.role not in ("super_admin", "agent_admin"):
            raise HTTPException(404, "Agency not found")
        if ctx.role == "agent_admin" and ctx.agency_id != agency_id:
            raise HTTPException(404, "Agency not found")
        return agency

    @staticmethod
    def list_all(db: Session, ctx: UserContext) -> list[Agency]:
        if ctx.role == "super_admin":
            return db.query(Agency).all()
        if ctx.role == "agent_admin":
            return [AgencyService.get_by_id(db, ctx, ctx.agency_id)]
        return []

    @staticmethod
    def update(db: Session, ctx: UserContext, agency_id: int, data: AgencyUpdate) -> Agency:
        agency = AgencyService.get_by_id(db, ctx, agency_id)
        if ctx.role != "super_admin":
            raise HTTPException(403)
        for k, v in data.model_dump(exclude_unset=True).items():
            setattr(agency, k, v)
        db.commit()
        db.refresh(agency)
        return agency

    @staticmethod
    def suspend(db: Session, ctx: UserContext, agency_id: int) -> Agency:
        if ctx.role != "super_admin":
            raise HTTPException(403)
        agency = AgencyService.get_by_id(db, ctx, agency_id)
        agency.status = 2
        db.commit()
        db.refresh(agency)
        return agency
