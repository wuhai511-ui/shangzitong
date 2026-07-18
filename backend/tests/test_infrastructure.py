"""Tests for project infrastructure: config, database, FastAPI app."""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestConfig:
    """RED: Config module not yet created."""

    def test_config_loads_from_env(self):
        """Config should load JWT_SECRET and DATABASE_URL from environment."""
        from core.config import Settings
        import os
        os.environ['JWT_SECRET'] = 'test-secret'
        os.environ['DATABASE_URL'] = 'sqlite:///test.db'
        settings = Settings()
        assert settings.JWT_SECRET == 'test-secret'
        assert settings.DATABASE_URL == 'sqlite:///test.db'
        assert settings.JWT_ALGORITHM == 'HS256'
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 1440

    def test_config_defaults(self):
        """Config should have sensible defaults."""
        from core.config import Settings
        # Clear env for defaults
        for k in ['JWT_SECRET', 'DATABASE_URL']:
            os.environ.pop(k, None)
        settings = Settings()
        assert settings.JWT_ALGORITHM == 'HS256'
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 1440


class TestDatabase:
    """RED: Database module not yet created."""

    def test_engine_created(self):
        """Database module should create SQLAlchemy engine."""
        from core.database import engine
        assert engine is not None
        assert 'sqlite' in str(engine.url)

    def test_session_created(self):
        """SessionLocal should be usable as context manager."""
        from core.database import SessionLocal
        with SessionLocal() as session:
            result = session.execute(
                __import__('sqlalchemy').text("SELECT 1")
            ).scalar()
            assert result == 1


class TestApp:
    """RED: FastAPI app not yet created."""

    def test_app_created(self):
        """main.py should expose a FastAPI app instance."""
        from app.main import app
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)
        assert app.title is not None

    def test_health_check(self):
        """GET /health should return 200."""
        from app.main import app
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
