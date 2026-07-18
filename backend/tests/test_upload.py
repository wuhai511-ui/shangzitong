"""RED: Tests for file upload ingest — smart column detection and import."""
import pytest
import sys, os, io
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestSmartColumnDetection:
    """Test intelligent column recognition (RED — not yet created)."""

    def test_detect_date_column_by_chinese_name(self):
        """Should detect column named '结算日期' as date column."""
        from app.ingest.upload_ingest import UploadIngest
        import pandas as pd
        df = pd.DataFrame({"结算日期": ["2026-01-15"], "金额": [3500.0]})
        ingest = UploadIngest()
        mappings = ingest._auto_detect_columns(df)
        assert mappings['date_column'] == '结算日期'

    def test_detect_amount_column_by_keyword(self):
        """Should detect column named '结算金额' as amount column."""
        from app.ingest.upload_ingest import UploadIngest
        import pandas as pd
        df = pd.DataFrame({"交易日": ["2026-01-15"], "结算金额": [3500.0]})
        ingest = UploadIngest()
        mappings = ingest._auto_detect_columns(df)
        assert mappings['amount_column'] == '结算金额'

    def test_detect_english_columns(self):
        """Should detect English column names."""
        from app.ingest.upload_ingest import UploadIngest
        import pandas as pd
        df = pd.DataFrame({"settle_date": ["2026-01-15"], "amount": [3500.0]})
        ingest = UploadIngest()
        mappings = ingest._auto_detect_columns(df)
        assert mappings['date_column'] == 'settle_date'
        assert mappings['amount_column'] == 'amount'

    def test_guess_date_format(self):
        """Should guess yyyy-MM-dd format."""
        from app.ingest.upload_ingest import UploadIngest
        ingest = UploadIngest()
        fmt = ingest._guess_date_format("2026-01-15")
        assert fmt == "%Y-%m-%d"

    def test_guess_date_format_yyyymmdd(self):
        """Should guess yyyyMMdd format."""
        from app.ingest.upload_ingest import UploadIngest
        ingest = UploadIngest()
        fmt = ingest._guess_date_format("20260115")
        assert fmt == "%Y%m%d"


class TestAmountCleaning:
    """Test amount string cleaning (RED — not yet created)."""

    def test_clean_comma_separated(self):
        """'1,234.56' → 1234.56"""
        from app.ingest.upload_ingest import UploadIngest
        ingest = UploadIngest()
        result = ingest._clean_amount("1,234.56")
        assert result == pytest.approx(1234.56)

    def test_clean_yuan_symbol(self):
        """'¥5000.00' → 5000.00"""
        from app.ingest.upload_ingest import UploadIngest
        ingest = UploadIngest()
        result = ingest._clean_amount("¥5000.00")
        assert result == pytest.approx(5000.0)


class TestUploadAPI:
    """Test file upload API endpoints (RED — not yet created)."""

    @pytest.fixture
    def client(self):
        from app.main import app
        from app.core.database import engine
        from models.base import Base
        Base.metadata.create_all(bind=engine)
        from fastapi.testclient import TestClient
        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        resp = client.post("/api/v1/auth/login", json={"code": "test_upload_user"})
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_upload_csv_preview(self, client, auth_headers):
        """POST /api/v1/ingest/upload/preview should return column mappings."""
        csv_content = b"date,amount\n2026-01-15,3500.00\n2026-01-16,4200.00"
        resp = client.post(
            "/api/v1/ingest/upload/preview",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
            headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "mappings" in data
        assert data["total_rows"] == 2

    def test_upload_confirm_import(self, client, auth_headers):
        """POST /api/v1/ingest/upload/confirm should import settlements."""
        # First upload for preview
        csv_content = b"date,amount\n2026-01-15,3500.00"
        preview_resp = client.post(
            "/api/v1/ingest/upload/preview",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
            headers=auth_headers
        )
        mappings = preview_resp.json()["mappings"]

        # Then confirm import
        resp = client.post(
            "/api/v1/ingest/upload/confirm",
            json={"mappings": mappings, "provider": "other"},
            headers=auth_headers
        )
        assert resp.status_code == 200
        assert resp.json()["imported"] >= 1
