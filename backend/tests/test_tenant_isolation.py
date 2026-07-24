"""Tenant isolation tests — verify role-based data access enforcement."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest
from core.database import SessionLocal
from core.auth_context import UserContext
from models.agency import Agency
from models.user import User


def _agency(db, name, status=0):
    a = Agency(name=name, contact_name="Test", contact_phone="13800000000", status=status)
    db.add(a)
    db.flush()
    _id = a.id
    db.commit()
    return _id


def _user(db, openid, agency_id, role="merchant"):
    u = User(openid=openid, nickname=openid, agency_id=agency_id, role=role)
    db.add(u)
    db.flush()
    _id = u.id
    db.commit()
    return _id


def _suffix(request):
    return request.node.name.replace("[", "_").replace("]", "_").replace(" ", "_")


class TestTenantIsolation:
    def test_agent_admin_can_see_own_agency(self, monkeypatch, request):
        from services.agency_service import AgencyService

        with SessionLocal() as db:
            a_id = _agency(db, "Agent-Agency-1")
            _user(db, f"h5:agent1-{_suffix(request)}", a_id, "agent_admin")
        ctx = UserContext(role="agent_admin", agency_id=a_id, user_id=999)

        with SessionLocal() as db:
            result = AgencyService.get_by_id(db, ctx, a_id)
            assert result.id == a_id

    def test_agent_admin_cannot_see_other_agency(self, monkeypatch, request):
        from services.agency_service import AgencyService

        with SessionLocal() as db:
            a1_id = _agency(db, "Agent-Agency-1")
            a2_id = _agency(db, "Agent-Agency-2")
            _user(db, f"h5:agent1-{_suffix(request)}", a1_id, "agent_admin")
        ctx = UserContext(role="agent_admin", agency_id=a1_id, user_id=999)

        with SessionLocal() as db:
            with pytest.raises(Exception) as exc:
                AgencyService.get_by_id(db, ctx, a2_id)
            assert exc.value.status_code == 404

    def test_agent_admin_list_only_returns_own_agency(self, monkeypatch, request):
        from services.agency_service import AgencyService

        with SessionLocal() as db:
            a1_id = _agency(db, "Agent-Agency-1")
            _agency(db, "Agent-Agency-2")
            _user(db, f"h5:agent1-{_suffix(request)}", a1_id, "agent_admin")
        ctx = UserContext(role="agent_admin", agency_id=a1_id, user_id=999)

        with SessionLocal() as db:
            agencies = AgencyService.list_all(db, ctx)
            assert len(agencies) == 1
            assert agencies[0].id == a1_id

    def test_merchant_list_returns_empty(self, monkeypatch, request):
        from services.agency_service import AgencyService

        with SessionLocal() as db:
            a_id = _agency(db, "Merc-Agency")
            _user(db, f"h5:merc1-{_suffix(request)}", a_id, "merchant")
        ctx = UserContext(role="merchant", agency_id=a_id, user_id=1001)

        with SessionLocal() as db:
            agencies = AgencyService.list_all(db, ctx)
            assert agencies == []

    def test_merchant_cannot_get_agency_directly(self, monkeypatch, request):
        from services.agency_service import AgencyService

        with SessionLocal() as db:
            a_id = _agency(db, "Merc-Agency")
            _user(db, f"h5:merc1-{_suffix(request)}", a_id, "merchant")
        ctx = UserContext(role="merchant", agency_id=a_id, user_id=1001)

        with SessionLocal() as db:
            with pytest.raises(Exception) as exc:
                AgencyService.get_by_id(db, ctx, a_id)
            assert exc.value.status_code == 404

    def test_super_admin_sees_all_agencies(self, monkeypatch, request):
        from services.agency_service import AgencyService

        with SessionLocal() as db:
            _agency(db, "SA-Agency-1")
            _agency(db, "SA-Agency-2")
        ctx = UserContext(role="super_admin", agency_id=None, user_id=1)

        with SessionLocal() as db:
            agencies = AgencyService.list_all(db, ctx)
            assert len(agencies) >= 2

    def test_require_super_admin_blocks_merchant(self, monkeypatch):
        ctx = UserContext(role="merchant", agency_id=1, user_id=100)
        with pytest.raises(Exception) as exc:
            ctx.require_super_admin()
        assert exc.value.status_code == 403

    def test_require_agent_blocks_merchant(self, monkeypatch):
        ctx = UserContext(role="merchant", agency_id=1, user_id=100)
        with pytest.raises(Exception) as exc:
            ctx.require_agent()
        assert exc.value.status_code == 403

    def test_require_agent_allows_agent_admin(self, monkeypatch):
        ctx = UserContext(role="agent_admin", agency_id=1, user_id=100)
        ctx.require_agent()

    def test_require_merchant_owner_allows_own_id(self, monkeypatch):
        ctx = UserContext(role="merchant", agency_id=1, user_id=100)
        ctx.require_merchant_owner(100)

    def test_require_merchant_owner_rejects_other_id(self, monkeypatch):
        ctx = UserContext(role="merchant", agency_id=1, user_id=100)
        with pytest.raises(Exception) as exc:
            ctx.require_merchant_owner(200)
        assert exc.value.status_code == 404
