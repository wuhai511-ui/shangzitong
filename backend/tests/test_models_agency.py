import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestAgencyModel:

    def test_create_agency(self):
        from models.agency import Agency
        from core.database import SessionLocal

        with SessionLocal() as session:
            agency = Agency(
                name="Test Agency",
                contact_name="Contact Person",
                contact_phone="12345678901"
            )
            session.add(agency)
            session.commit()
            session.refresh(agency)

            assert agency.id is not None
            assert agency.name == "Test Agency"
            assert agency.contact_name == "Contact Person"
            assert agency.contact_phone == "12345678901"
            assert agency.status == 0
            assert agency.created_at is not None
            assert agency.updated_at is not None
            assert agency.deleted_at is None
            assert agency.is_deleted is False

    def test_soft_delete(self):
        from models.agency import Agency
        from core.database import SessionLocal

        with SessionLocal() as session:
            agency = Agency(
                name="To Be Deleted",
                contact_name="Temp",
                contact_phone="00000000000"
            )
            session.add(agency)
            session.commit()

            agency.soft_delete()
            session.commit()
            session.refresh(agency)

            assert agency.deleted_at is not None
            assert agency.is_deleted is True
