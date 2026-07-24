import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestAgencyPaymentChannelModel:

    def test_create_channel(self):
        from models.agency_payment_channel import AgencyPaymentChannel, PaymentProvider
        from models.agency import Agency
        from core.database import SessionLocal

        with SessionLocal() as session:
            agency = Agency(
                name="Channel Test Agency",
                contact_name="Test",
                contact_phone="11111111111"
            )
            session.add(agency)
            session.commit()
            session.refresh(agency)

            channel = AgencyPaymentChannel(
                agency_id=agency.id,
                provider=PaymentProvider.lkl,
                org_no="ORG001",
                api_key_cipher="encrypted_key",
                api_secret_cipher="encrypted_secret",
            )
            session.add(channel)
            session.commit()
            session.refresh(channel)

            assert channel.id is not None
            assert channel.agency_id == agency.id
            assert channel.provider == PaymentProvider.lkl
            assert channel.org_no == "ORG001"
            assert channel.api_key_cipher == "encrypted_key"
            assert channel.api_secret_cipher == "encrypted_secret"
            assert channel.key_version == 1
            assert channel.status == 0
            assert channel.created_at is not None
            assert channel.updated_at is not None
            assert channel.deleted_at is None
            assert channel.is_deleted is False
