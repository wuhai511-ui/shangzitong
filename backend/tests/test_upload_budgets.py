"""Resource-budget regression tests for upload parsing and preview caching."""
import io

import pytest


class TestUploadParseBudgets:
    def test_csv_stops_after_max_rows_plus_one(self, monkeypatch):
        import app.ingest.upload_ingest as upload_module

        class CountingReader:
            fieldnames = ["date", "amount"]

            def __init__(self):
                self.pulls = 0

            def __iter__(self):
                return self

            def __next__(self):
                self.pulls += 1
                if self.pulls > 3:
                    raise AssertionError("CSV parser consumed past max_rows + 1")
                return {"date": "2026-01-15", "amount": "1.00"}

        reader = CountingReader()
        monkeypatch.setattr(upload_module.csv, "DictReader", lambda stream: reader)

        result = upload_module.UploadIngest().parse_upload(
            b"ignored",
            "large.csv",
            max_rows=2,
            max_columns=10,
            max_cells=100,
        )
        assert result.rows == []
        assert result.total_rows == 0
        assert "row limit" in result.errors[0].lower()
        assert reader.pulls == 3

    def test_csv_rejects_too_many_columns(self):
        from app.ingest.upload_ingest import UploadIngest

        result = UploadIngest().parse_upload(
            b"a,b,c\n1,2,3\n",
            "wide.csv",
            max_rows=10,
            max_columns=2,
            max_cells=100,
        )
        assert result.rows == []
        assert "column limit" in result.errors[0].lower()

    def test_csv_rejects_cell_budget_without_reading_remaining_rows(self):
        from app.ingest.upload_ingest import UploadIngest

        result = UploadIngest().parse_upload(
            b"a,b\n1,2\n3,4\n5,6\n7,8\n",
            "cells.csv",
            max_rows=10,
            max_columns=10,
            max_cells=4,
        )
        assert result.rows == []
        assert "cell limit" in result.errors[0].lower()

    def test_excel_uses_bounded_nrows_and_rejects_extra_row(self, monkeypatch):
        import app.ingest.upload_ingest as upload_module
        import pandas as pd

        calls = []

        def bounded_read_excel(*args, **kwargs):
            calls.append(kwargs)
            return pd.DataFrame(
                {
                    "date": ["2026-01-15", "2026-01-16", "2026-01-17"],
                    "amount": ["1", "2", "3"],
                }
            )

        monkeypatch.setattr(upload_module.pd, "read_excel", bounded_read_excel)
        result = upload_module.UploadIngest().parse_upload(
            b"PK ignored by parser unit test",
            "rows.xlsx",
            max_rows=2,
            max_columns=10,
            max_cells=100,
        )
        assert calls[0]["nrows"] == 3
        assert result.rows == []
        assert "row limit" in result.errors[0].lower()

    def test_excel_rejects_column_and_cell_budgets(self, monkeypatch):
        import app.ingest.upload_ingest as upload_module
        import pandas as pd

        monkeypatch.setattr(
            upload_module.pd,
            "read_excel",
            lambda *args, **kwargs: pd.DataFrame(
                [[1, 2, 3]], columns=["a", "b", "c"]
            ),
        )
        too_wide = upload_module.UploadIngest().parse_upload(
            b"PK", "wide.xlsx", max_rows=10, max_columns=2, max_cells=100
        )
        too_many_cells = upload_module.UploadIngest().parse_upload(
            b"PK", "cells.xlsx", max_rows=10, max_columns=10, max_cells=2
        )
        assert "column limit" in too_wide.errors[0].lower()
        assert "cell limit" in too_many_cells.errors[0].lower()


class TestUploadPreviewCacheBudgets:
    @pytest.fixture
    def client(self):
        from app.main import app
        from fastapi.testclient import TestClient

        return TestClient(app)

    @pytest.fixture
    def auth_headers(self, client):
        response = client.post("/api/v1/auth/login", json={"code": "budget_user"})
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    @pytest.fixture
    def second_auth_headers(self, client):
        response = client.post("/api/v1/auth/login", json={"code": "budget_user_2"})
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    @pytest.fixture(autouse=True)
    def clear_preview_store(self):
        from api.upload import _preview_store

        _preview_store.clear()
        yield
        _preview_store.clear()

    @staticmethod
    def post_preview(client, headers, content):
        return client.post(
            "/api/v1/ingest/upload/preview",
            files={"file": ("budget.csv", io.BytesIO(content), "text/csv")},
            headers=headers,
        )

    def test_preview_store_keeps_raw_bytes_but_not_materialized_rows(
        self, client, auth_headers
    ):
        from api.upload import _preview_store

        content = b"date,amount\n2026-01-15,1.00\n"
        response = self.post_preview(client, auth_headers, content)
        assert response.status_code == 200

        stored = _preview_store[response.json()["preview_id"]]
        assert stored["file_content"] == content
        assert "rows" not in stored
        assert stored["total_rows"] == 1

    def test_confirm_reparses_popped_bytes_with_same_budgets(
        self, client, auth_headers, monkeypatch
    ):
        import api.upload as upload_api
        from app.core.config import settings

        content = b"date,amount\n2026-01-15,1.00\n"
        preview = self.post_preview(client, auth_headers, content).json()
        original_parse = upload_api.UploadIngest.parse_upload
        calls = []

        def parse_spy(ingest, *args, **kwargs):
            calls.append((args, kwargs))
            return original_parse(ingest, *args, **kwargs)

        monkeypatch.setattr(upload_api.UploadIngest, "parse_upload", parse_spy)
        response = client.post(
            "/api/v1/ingest/upload/confirm",
            json={
                "preview_id": preview["preview_id"],
                "mappings": preview["mappings"],
                "provider": "budget-test",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["imported"] == 1
        assert len(calls) == 1
        assert calls[0][0][0] == content
        assert calls[0][1]["max_rows"] == settings.UPLOAD_MAX_ROWS
        assert calls[0][1]["max_columns"] == settings.UPLOAD_MAX_COLUMNS
        assert calls[0][1]["max_cells"] == settings.UPLOAD_MAX_CELLS

    def test_per_user_byte_budget_rejects_without_growing_store(
        self, client, auth_headers, monkeypatch
    ):
        import api.upload as upload_api

        content = b"date,amount\n2026-01-15,1.00\n"
        monkeypatch.setattr(upload_api, "MAX_PREVIEW_BYTES_PER_USER", len(content))
        monkeypatch.setattr(upload_api, "MAX_PREVIEW_BYTES_TOTAL", len(content) * 10)
        first = self.post_preview(client, auth_headers, content)
        assert first.status_code == 200
        before = dict(upload_api._preview_store)

        rejected = self.post_preview(client, auth_headers, content)
        assert rejected.status_code == 429
        assert upload_api._preview_store == before

    def test_global_byte_budget_rejects_without_growing_or_evicting(
        self, client, auth_headers, second_auth_headers, monkeypatch
    ):
        import api.upload as upload_api

        content = b"date,amount\n2026-01-15,1.00\n"
        monkeypatch.setattr(upload_api, "MAX_PREVIEW_BYTES_PER_USER", len(content) * 10)
        monkeypatch.setattr(upload_api, "MAX_PREVIEW_BYTES_TOTAL", len(content) * 2)
        assert self.post_preview(client, auth_headers, content).status_code == 200
        assert self.post_preview(client, second_auth_headers, content).status_code == 200
        before = dict(upload_api._preview_store)

        rejected = self.post_preview(client, auth_headers, content)
        assert rejected.status_code == 429
        assert upload_api._preview_store == before
