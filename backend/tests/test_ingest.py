"""RED: Tests for data ingest framework."""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestIngestAdapter:
    """Test IngestAdapter abstract base (RED)."""

    def test_adapter_is_abstract(self):
        """IngestAdapter should not be instantiable directly."""
        from app.ingest.adapter import IngestAdapter
        with pytest.raises(TypeError):
            IngestAdapter()

    def test_concrete_adapter_must_implement_methods(self):
        """Concrete adapter must override abstract methods."""
        from app.ingest.adapter import IngestAdapter

        class IncompleteAdapter(IngestAdapter):
            pass

        with pytest.raises(TypeError):
            IncompleteAdapter()


class TestSettlementWriter:
    """Test SettlementWriter (RED)."""

    def test_normalize_standardizes_fields(self):
        """normalize should produce Settlement with standard field names."""
        from app.ingest.writer import SettlementWriter
        from datetime import date
        from decimal import Decimal

        writer = SettlementWriter()
        raw = {"date": "2026-01-15", "amount": "3500.50"}
        result = writer.normalize(raw, source_id=1, provider="test")

        assert result["settle_date"] == date(2026, 1, 15)
        assert result["amount"] == Decimal("3500.50")
        assert result["source_id"] == 1
        assert result["provider"] == "test"

    def test_dedup_skips_duplicates(self):
        """dedup_and_insert should skip entries already in DB."""
        from app.ingest.writer import SettlementWriter
        from app.models.datasource import DataSource
        from app.core.database import SessionLocal, engine
        from app.models.base import Base
        from decimal import Decimal
        from datetime import date

        Base.metadata.create_all(bind=engine)

        # Create a data source
        db = SessionLocal()
        ds = DataSource(user_id=1, source_type="upload", provider="test", label="test")
        db.add(ds)
        db.commit()

        writer = SettlementWriter()
        settlements = [
            {"settle_date": date(2026, 1, 15), "amount": Decimal("1000"),
             "source_id": ds.id, "provider": "test", "user_id": 1}
        ]

        # First insert
        count1 = writer.dedup_and_insert(settlements, source=ds, db=db)
        assert count1 == 1

        # Second insert with same data
        count2 = writer.dedup_and_insert(settlements, source=ds, db=db)
        assert count2 == 0  # Should skip duplicate

        db.close()
