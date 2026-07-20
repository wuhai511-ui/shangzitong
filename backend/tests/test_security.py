"""Tests for JWT security tools — TDD Module 1.3: RED phase."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import time
import pytest
from fastapi.testclient import TestClient
from core.config import settings


@pytest.fixture
def client():
    from app.main import app

    return TestClient(app)


def create_cookie_session(client, username="csrf-user"):
    response = client.post(
        "/api/v1/auth/session",
        headers={settings.H5_TRUSTED_HEADER: username},
    )
    assert response.status_code == 200
    return response.cookies["szt_csrf"]


class TestJWT:
    """JWT token creation and verification tests."""

    def test_create_and_verify_token(self):
        """create_access_token should produce a token that verify_token can decode."""
        from core.security import create_access_token, verify_token

        data = {"user_id": 42, "role": "user"}
        token = create_access_token(data)
        assert isinstance(token, str)
        assert len(token) > 0

        payload = verify_token(token)
        assert payload["user_id"] == 42
        assert payload["role"] == "user"

    def test_expired_token(self):
        """verify_token should raise an error for expired tokens."""
        from core.security import create_access_token, verify_token

        data = {"user_id": 42}
        # Token with -1 minute expiry
        token = create_access_token(data, expires_delta=-60)
        with pytest.raises(Exception):
            verify_token(token)

    def test_invalid_token(self):
        """verify_token should raise an error for malformed tokens."""
        from core.security import verify_token

        with pytest.raises(Exception):
            verify_token("not.a.valid.token")

        with pytest.raises(Exception):
            verify_token("")


class TestCSRFProtection:
    def test_cookie_mutation_requires_csrf_header(self, client):
        create_cookie_session(client)

        response = client.put(
            "/api/v1/profile/cash",
            json={"available_cash": "1.00"},
        )

        assert response.status_code == 403
        assert response.json() == {"detail": "CSRF validation failed"}

    def test_cookie_mutation_rejects_mismatched_csrf_header(self, client):
        create_cookie_session(client)

        response = client.put(
            "/api/v1/profile/cash",
            json={"available_cash": "1.00"},
            headers={"X-CSRF-Token": "not-the-cookie-token"},
        )

        assert response.status_code == 403
        assert response.json() == {"detail": "CSRF validation failed"}

    def test_cookie_mutation_accepts_matching_csrf_header(self, client):
        csrf_token = create_cookie_session(client)

        response = client.put(
            "/api/v1/profile/cash",
            json={"available_cash": "1.00"},
            headers={"X-CSRF-Token": csrf_token},
        )

        assert response.status_code == 200

    def test_bearer_mutation_remains_compatible_with_stale_cookie(self, client):
        login = client.post(
            "/api/v1/auth/login",
            json={"code": "csrf-bearer-user"},
        )
        client.cookies.set(settings.H5_COOKIE_NAME, "stale-session")

        response = client.put(
            "/api/v1/profile/cash",
            json={"available_cash": "1.00"},
            headers={
                "Authorization": f"Bearer {login.json()['access_token']}",
            },
        )

        assert response.status_code == 200
