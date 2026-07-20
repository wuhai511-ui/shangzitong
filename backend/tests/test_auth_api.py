"""Tests for WeChat login API — TDD Module 1.4: RED phase."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest
from fastapi.testclient import TestClient
from core.config import settings


@pytest.fixture
def client():
    """Create a test client. Import app lazily to avoid side effects."""
    from app.main import app
    return TestClient(app)


class TestAuthAPI:
    """Auth API tests."""

    def test_login_create_user(self, client):
        """POST /api/v1/auth/login with a new code should create user and return token."""
        resp = client.post("/api/v1/auth/login", json={"code": "test_user_001"})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["openid"] == "test_user_001"
        assert data["user"]["nickname"].startswith("用户_")

    def test_login_existing_user(self, client):
        """POST /api/v1/auth/login with an existing code should return token for same user."""
        # First login creates the user
        resp1 = client.post("/api/v1/auth/login", json={"code": "test_user_002"})
        assert resp1.status_code == 200
        user1 = resp1.json()["user"]

        # Second login returns the same user
        resp2 = client.post("/api/v1/auth/login", json={"code": "test_user_002"})
        assert resp2.status_code == 200
        user2 = resp2.json()["user"]
        assert user2["id"] == user1["id"]
        assert user2["openid"] == user1["openid"]

    def test_get_me(self, client):
        """GET /api/v1/auth/me with valid token should return current user."""
        # Login first
        resp = client.post("/api/v1/auth/login", json={"code": "test_user_003"})
        token = resp.json()["access_token"]

        # Call /me
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["openid"] == "test_user_003"

    def test_unauthorized(self, client):
        """GET /api/v1/auth/me without token should return 401."""
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

        # Also test with invalid token
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert resp.status_code == 401

    def test_trusted_header_creates_cookie_session(self, client):
        response = client.post(
            "/api/v1/auth/session",
            headers={"X-Authenticated-User": "szt"},
        )

        assert response.status_code == 200
        assert response.json()["openid"] == "h5:szt"
        assert response.cookies[settings.H5_COOKIE_NAME]
        assert response.cookies["szt_csrf"]

        me = client.get("/api/v1/auth/me")
        assert me.status_code == 200
        assert me.json()["openid"] == "h5:szt"

    @pytest.mark.parametrize(
        "headers",
        [
            {},
            {"X-Authenticated-User": ""},
            {"X-Authenticated-User": "   "},
        ],
    )
    def test_trusted_session_rejects_missing_or_blank_identity(self, client, headers):
        response = client.post("/api/v1/auth/session", headers=headers)

        assert response.status_code == 401
        assert response.json() == {"detail": "Not authenticated"}
        assert settings.H5_COOKIE_NAME not in response.cookies
        assert "szt_csrf" not in response.cookies

    def test_trusted_session_rejects_oversized_identity(self, client):
        response = client.post(
            "/api/v1/auth/session",
            headers={"X-Authenticated-User": "x" * 125},
        )

        assert response.status_code == 401
        assert response.json() == {"detail": "Not authenticated"}
        assert settings.H5_COOKIE_NAME not in response.cookies
        assert "szt_csrf" not in response.cookies

    def test_session_cookies_have_h5_security_attributes(self, client):
        response = client.post(
            "/api/v1/auth/session",
            headers={"X-Authenticated-User": "cookie-flags"},
        )

        set_cookie_headers = response.headers.get_list("set-cookie")
        session_cookie = next(
            header for header in set_cookie_headers
            if header.startswith(f"{settings.H5_COOKIE_NAME}=")
        ).lower()
        csrf_cookie = next(
            header for header in set_cookie_headers
            if header.startswith("szt_csrf=")
        ).lower()
        expected_max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        assert "httponly" in session_cookie
        assert "httponly" not in csrf_cookie
        for cookie in (session_cookie, csrf_cookie):
            assert "path=/" in cookie
            assert "samesite=lax" in cookie
            assert f"max-age={expected_max_age}" in cookie
            assert ("secure" in cookie) is (settings.ENV == "prod")

    def test_session_cookies_are_secure_in_production(self, client, monkeypatch):
        monkeypatch.setattr(settings, "ENV", "prod")

        response = client.post(
            "/api/v1/auth/session",
            headers={"X-Authenticated-User": "prod-cookie-flags"},
        )

        set_cookie_headers = response.headers.get_list("set-cookie")
        session_cookie = next(
            header for header in set_cookie_headers
            if header.startswith(f"{settings.H5_COOKIE_NAME}=")
        )
        csrf_cookie = next(
            header for header in set_cookie_headers if header.startswith("szt_csrf=")
        )
        assert all("Secure" in cookie for cookie in (session_cookie, csrf_cookie))

    def test_session_bootstrap_ignores_stale_cookie_without_csrf(self, client):
        client.cookies.set(settings.H5_COOKIE_NAME, "stale-session")

        response = client.post(
            "/api/v1/auth/session",
            headers={"X-Authenticated-User": "fresh-session"},
        )

        assert response.status_code == 200
        assert response.json()["openid"] == "h5:fresh-session"

    def test_session_response_hides_token_and_replaces_stale_cookies(self, client):
        client.cookies.set(settings.H5_COOKIE_NAME, "stale-session")
        client.cookies.set("szt_csrf", "stale-csrf")

        response = client.post(
            "/api/v1/auth/session",
            headers={"X-Authenticated-User": "rotated-session"},
        )

        assert response.status_code == 200
        assert "access_token" not in response.json()
        assert response.cookies[settings.H5_COOKIE_NAME]
        assert response.cookies["szt_csrf"]
        assert response.cookies[settings.H5_COOKIE_NAME] != "stale-session"
        assert response.cookies["szt_csrf"] != "stale-csrf"
