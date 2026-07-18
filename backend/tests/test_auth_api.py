"""Tests for WeChat login API — TDD Module 1.4: RED phase."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest
from fastapi.testclient import TestClient


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
