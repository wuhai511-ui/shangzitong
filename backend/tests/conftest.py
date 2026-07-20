"""Pytest fixtures for backend tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

# Set dev JWT secret before any imports
os.environ['JWT_SECRET'] = 'dev-test-secret-key-for-pytest-only-32bytes!'
os.environ['DATABASE_URL'] = 'sqlite:///./test_szt.db'

import pytest

from core.database import engine
from models.base import Base
from models.user import User  # noqa
from models.card import Card  # noqa
from models.datasource import DataSource, Settlement  # noqa
from models.merchant_profile import MerchantProfile  # noqa


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Create all tables before tests and drop them after."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
