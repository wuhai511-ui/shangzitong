"""Database initialization performed during application startup."""
from core.config import settings
from core.database import SessionLocal, engine
from models.base import Base
from models.bank import Bank, DEFAULT_BANKS


def initialize_database() -> None:
    """Validate production settings, create tables, and seed banks once."""
    settings.validate_production()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        if db.query(Bank).count() == 0:
            db.add_all(
                Bank(name=name, code=code, sort_order=index)
                for index, (name, code) in enumerate(DEFAULT_BANKS)
            )
            db.commit()
