import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestMerchantModel:

    def test_create_merchant(self):
        from models.merchant import Merchant
        from core.database import SessionLocal

        with SessionLocal() as session:
            merchant = Merchant(
                agency_id=1,
                name="Test Store",
                phone="13800001111",
                business_type="retail",
                is_micro=True,
                auto_swipe_enabled=False,
            )
            session.add(merchant)
            session.commit()
            session.refresh(merchant)

            assert merchant.id is not None
            assert merchant.name == "Test Store"
            assert merchant.phone == "13800001111"
            assert merchant.business_type == "retail"
            assert merchant.is_micro is True
            assert merchant.auto_swipe_enabled is False
            assert merchant.created_at is not None
            assert merchant.updated_at is not None
            assert merchant.deleted_at is None

    def test_merchant_soft_delete(self):
        from models.merchant import Merchant
        from core.database import SessionLocal

        with SessionLocal() as session:
            merchant = Merchant(
                agency_id=1,
                name="Delete Me",
            )
            session.add(merchant)
            session.commit()

            merchant.soft_delete()
            session.commit()
            session.refresh(merchant)

            assert merchant.deleted_at is not None
            assert merchant.is_deleted is True


class TestMerchantOnboardingModel:

    def test_create_application(self):
        from models.merchant_onboarding import MerchantOnboardingApplication, OnboardingStatus
        from core.database import SessionLocal

        with SessionLocal() as session:
            app = MerchantOnboardingApplication(
                agency_id=1,
                merchant_id=1,
                agency_payment_channel_id=1,
                provider="lkl",
                status=OnboardingStatus.pending,
                is_simulated=False,
            )
            session.add(app)
            session.commit()
            session.refresh(app)

            assert app.id is not None
            assert app.status == OnboardingStatus.pending
            assert app.provider == "lkl"
            assert app.is_simulated is False
            assert app.created_at is not None

    def test_status_enum_values(self):
        from models.merchant_onboarding import OnboardingStatus

        assert OnboardingStatus.pending.value == "pending"
        assert OnboardingStatus.submitted.value == "submitted"
        assert OnboardingStatus.approved.value == "approved"
        assert OnboardingStatus.rejected.value == "rejected"
