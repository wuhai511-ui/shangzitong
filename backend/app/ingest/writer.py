"""Standardize raw settlements and insert with dedup into DB."""
from datetime import date
from decimal import Decimal
from sqlalchemy import text


class SettlementWriter:
    """Format normalization and deduplicated insert for settlement data."""

    def normalize(self, raw: dict, source_id: int, provider: str) -> dict:
        """Convert raw dict to standardized settlement fields."""
        settle_date = raw.get("settle_date") or raw.get("date")
        if isinstance(settle_date, str):
            from datetime import datetime
            for fmt in ["%Y-%m-%d", "%Y%m%d", "%m/%d/%Y"]:
                try:
                    settle_date = datetime.strptime(settle_date, fmt).date()
                    break
                except ValueError:
                    continue

        amount = raw.get("amount", 0)
        if isinstance(amount, str):
            amount = float(amount.replace(",", "").replace("¥", "").replace("$", ""))
        amount = Decimal(str(amount))

        return {
            "settle_date": settle_date,
            "amount": amount,
            "source_id": source_id,
            "provider": provider,
        }

    def dedup_and_insert(self, settlements: list[dict], source, db) -> int:
        """Insert settlements, skipping duplicates. Returns count of new rows."""
        inserted = 0
        for s in settlements:
            # Check for duplicate
            existing = db.execute(
                text(
                    "SELECT id FROM settlements WHERE source_id = :sid "
                    "AND settle_date = :sd AND amount = :amt AND provider = :pr"
                ),
                {
                    "sid": s.get("source_id", source.id),
                    "sd": s.get("settle_date"),
                    "amt": str(s.get("amount", 0)),
                    "pr": s.get("provider", ""),
                },
            ).first()

            if existing:
                continue

            db.execute(
                text(
                    "INSERT INTO settlements (source_id, user_id, settle_date, "
                    "amount, provider, created_at) "
                    "VALUES (:sid, :uid, :sd, :amt, :pr, datetime('now'))"
                ),
                {
                    "sid": s.get("source_id", source.id),
                    "uid": s.get("user_id", source.user_id),
                    "sd": s.get("settle_date"),
                    "amt": str(s.get("amount", 0)),
                    "pr": s.get("provider", ""),
                },
            )
            inserted += 1

        db.commit()
        return inserted
