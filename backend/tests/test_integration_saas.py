"""Integration test: full multi-tenant SaaS flow — create agency, channel, merchant, and verify tenant isolation."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import pytest
from core.database import SessionLocal
from core.auth_context import UserContext
from core.crypto import encrypt_field, decrypt_field, mask_value
from models.agency import Agency
from models.agency_payment_channel import AgencyPaymentChannel, PaymentProvider
from models.merchant import Merchant
from models.merchant_onboarding import MerchantOnboardingApplication
from services.agency_service import AgencyService
from services.channel_service import ChannelService
from services.merchant_service import MerchantService
from schemas.agency import AgencyCreate, AgencyUpdate
from schemas.channel import ChannelCreate
from schemas.merchant import MerchantCreate


class TestSaaSIntegration:
    def test_full_agency_lifecycle(self):
        super_ctx = UserContext(role="super_admin", agency_id=None, user_id=1)

        with SessionLocal() as db:
            agency = AgencyService.create(db, super_ctx, AgencyCreate(name="TestCorp", contact_name="CEO"))
            assert agency.id is not None
            assert agency.status == 0

            AgencyService.update(db, super_ctx, agency.id, AgencyUpdate(status=1))
            db.refresh(agency)
            assert agency.status == 1

            AgencyService.suspend(db, super_ctx, agency.id)
            db.refresh(agency)
            assert agency.status == 2

    def test_channel_credential_encryption_roundtrip(self):
        super_ctx = UserContext(role="super_admin", agency_id=None, user_id=1)

        with SessionLocal() as db:
            agency = AgencyService.create(db, super_ctx, AgencyCreate(name="CryptoCorp"))
            agent_ctx = UserContext(role="agent_admin", agency_id=agency.id, user_id=2)
            channel = ChannelService.create(db, agent_ctx, ChannelCreate(
                provider="lkl", org_no="ORG001", api_key="sk_test_abc123", api_secret="secret_xyz"
            ))
            assert channel.api_key_cipher != "sk_test_abc123"
            assert channel.api_secret_cipher != "secret_xyz"
            assert decrypt_field(channel.api_key_cipher) == "sk_test_abc123"

    def test_merchant_tenant_isolation(self):
        super_ctx = UserContext(role="super_admin", agency_id=None, user_id=1)

        with SessionLocal() as db:
            a1 = AgencyService.create(db, super_ctx, AgencyCreate(name="Agent1"))
            a2 = AgencyService.create(db, super_ctx, AgencyCreate(name="Agent2"))
            AgencyService.update(db, super_ctx, a1.id, AgencyUpdate(status=1))

            ctx1 = UserContext(role="agent_admin", agency_id=a1.id, user_id=10)
            ch = ChannelService.create(db, ctx1, ChannelCreate(provider="lkl", org_no="ORG1", api_key="k1", api_secret="s1"))
            m1 = MerchantService.create_merchant_with_onboarding(
                db, ctx1, MerchantCreate(name="M1", channel_id=ch.id)
            )
            assert m1.agency_id == a1.id

            ctx2 = UserContext(role="agent_admin", agency_id=a2.id, user_id=20)
            merchants = MerchantService.list_by_agency(db, ctx2, a2.id)
            assert len([m for m in merchants if m.id == m1.id]) == 0

    def test_crypto_mask_value(self):
        assert mask_value("6222021234567890") == "************7890"
