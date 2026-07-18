"""Tests for JWT security tools — TDD Module 1.3: RED phase."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import time
import pytest


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
