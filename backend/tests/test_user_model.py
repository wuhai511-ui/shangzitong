"""Tests for User model — TDD Module 1.2: RED phase."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestUserModel:
    """User model tests."""

    def test_create_user(self):
        """Should create a User with all required fields."""
        from models.user import User
        from core.database import SessionLocal

        with SessionLocal() as session:
            user = User(
                openid="wx_test_openid_001",
                nickname="测试用户",
                phone="encrypted_phone_value"
            )
            session.add(user)
            session.commit()
            session.refresh(user)

            assert user.id is not None
            assert user.openid == "wx_test_openid_001"
            assert user.nickname == "测试用户"
            assert user.phone == "encrypted_phone_value"
            assert user.created_at is not None
            assert user.updated_at is not None
            assert user.deleted_at is None
            assert user.is_deleted is False

    def test_soft_delete(self):
        """soft_delete() should set deleted_at and is_deleted should return True."""
        from models.user import User
        from core.database import SessionLocal

        with SessionLocal() as session:
            user = User(
                openid="wx_test_openid_002",
                nickname="待删除用户",
                phone="encrypted_phone_value"
            )
            session.add(user)
            session.commit()

            user.soft_delete()
            session.commit()
            session.refresh(user)

            assert user.deleted_at is not None
            assert user.is_deleted is True

    def test_unique_openid(self):
        """openid should be unique — inserting duplicate should raise IntegrityError."""
        import pytest
        from sqlalchemy.exc import IntegrityError
        from models.user import User
        from core.database import SessionLocal

        with SessionLocal() as session:
            user1 = User(
                openid="wx_test_openid_003",
                nickname="用户A",
                phone="encrypted_phone_value"
            )
            session.add(user1)
            session.commit()

            user2 = User(
                openid="wx_test_openid_003",  # same openid
                nickname="用户B",
                phone="encrypted_phone_value"
            )
            session.add(user2)
            with pytest.raises(IntegrityError):
                session.commit()
