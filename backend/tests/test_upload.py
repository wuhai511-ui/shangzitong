"""RED: Tests for file upload ingest — smart column detection and import."""
from datetime import datetime, timedelta, timezone
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




class TestSecureUploadPreviewAPI:
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
        response = client.post("/api/v1/auth/login", json={"code": "secure_upload_user"})
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    @pytest.fixture
    def second_auth_headers(self, client):
        response = client.post("/api/v1/auth/login", json={"code": "secure_upload_user_2"})
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    @pytest.fixture(autouse=True)
    def clear_preview_store(self):
        from api.upload import _preview_store
        _preview_store.clear()
        yield
        _preview_store.clear()

    @staticmethod
    def create_preview(client, headers, *, filename="test.csv", body=None):
        content = body or b"date,amount\n2026-01-15,3500.00"
        response = client.post(
            "/api/v1/ingest/upload/preview",
            files={"file": (filename, io.BytesIO(content), "text/csv")},
            headers=headers,
        )
        assert response.status_code == 200
        return response.json()

    @staticmethod
    def confirm_preview(client, headers, preview_id, mappings=None):
        return client.post(
            "/api/v1/ingest/upload/confirm",
            json={
                "preview_id": preview_id,
                "mappings": mappings or {
                    "date_column": "date",
                    "amount_column": "amount",
                    "date_format": "%Y-%m-%d",
                },
                "provider": "other",
            },
            headers=headers,
        )

    def test_preview_returns_random_id_and_expiry(self, client, auth_headers):
        first = self.create_preview(client, auth_headers)
        second = self.create_preview(client, auth_headers)

        assert len(first["preview_id"]) == 32
        assert first["preview_id"] != second["preview_id"]
        assert datetime.fromisoformat(first["expires_at"]) > datetime.now(timezone.utc)

    def test_upload_rejects_more_than_10_mib(self, client, auth_headers):
        body = b"a" * (10 * 1024 * 1024 + 1)
        response = client.post(
            "/api/v1/ingest/upload/preview",
            files={"file": ("large.csv", io.BytesIO(body), "text/csv")},
            headers=auth_headers,
        )
        assert response.status_code == 413

    @pytest.mark.parametrize(
        ("filename", "content"),
        [
            ("payload.exe", b"date,amount\n2026-01-15,1.00"),
            ("fake.xlsx", b"not a zip workbook"),
            ("nul.csv", b"date,amount\n2026-01-15,1.00\x00"),
        ],
    )
    def test_upload_rejects_disallowed_or_invalid_content(
        self, client, auth_headers, filename, content
    ):
        response = client.post(
            "/api/v1/ingest/upload/preview",
            files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_preview_is_owned_and_one_time(
        self, client, auth_headers, second_auth_headers
    ):
        preview_id = self.create_preview(client, auth_headers)["preview_id"]

        foreign = self.confirm_preview(client, second_auth_headers, preview_id)
        assert foreign.status_code == 404
        assert self.confirm_preview(client, auth_headers, preview_id).status_code == 200
        assert self.confirm_preview(client, auth_headers, preview_id).status_code == 400

    def test_expired_preview_cannot_be_confirmed(self, client, auth_headers):
        from api.upload import _preview_store

        preview_id = self.create_preview(client, auth_headers)["preview_id"]
        _preview_store[preview_id]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)

        response = self.confirm_preview(client, auth_headers, preview_id)
        assert response.status_code == 400
        assert preview_id not in _preview_store

    def test_legacy_confirm_consumes_users_latest_valid_preview(
        self, client, auth_headers
    ):
        older = self.create_preview(
            client, auth_headers, body=b"date,amount\nnot-a-date,1.00"
        )
        newer = self.create_preview(client, auth_headers)

        response = client.post(
            "/api/v1/ingest/upload/confirm",
            json={
                "mappings": {
                    "date_column": "date",
                    "amount_column": "amount",
                    "date_format": "%Y-%m-%d",
                },
                "provider": "legacy",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["imported"] == 1

        from api.upload import _preview_store
        assert newer["preview_id"] not in _preview_store
        assert older["preview_id"] in _preview_store

    def test_legacy_confirm_never_consumes_another_users_preview(
        self, client, auth_headers, second_auth_headers
    ):
        preview_id = self.create_preview(client, auth_headers)["preview_id"]

        foreign = client.post(
            "/api/v1/ingest/upload/confirm",
            json={"mappings": {}, "provider": "legacy"},
            headers=second_auth_headers,
        )
        assert foreign.status_code == 400
        assert self.confirm_preview(client, auth_headers, preview_id).status_code == 200

    def test_legacy_confirm_with_only_expired_preview_returns_generic_error(
        self, client, auth_headers
    ):
        from api.upload import _preview_store

        preview_id = self.create_preview(client, auth_headers)["preview_id"]
        _preview_store[preview_id]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)

        response = client.post(
            "/api/v1/ingest/upload/confirm",
            json={"mappings": {}, "provider": "legacy"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "No preview data found"
        assert preview_id not in _preview_store
