import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestPaymentProviderFactory:

    def test_factory_returns_lkl_adapter(self):
        from payment import PaymentProviderFactory
        adapter = PaymentProviderFactory.get("lkl")
        from payment.lkl_adapter import LKLAdapter
        assert isinstance(adapter, LKLAdapter)

    def test_factory_returns_huifu_adapter(self):
        from payment import PaymentProviderFactory
        adapter = PaymentProviderFactory.get("huifu")
        from payment.huifu_adapter import HuifuAdapter
        assert isinstance(adapter, HuifuAdapter)

    def test_factory_returns_mock_adapter_in_test_mode(self):
        from payment import PaymentProviderFactory
        adapter = PaymentProviderFactory.get("lkl", test_mode=True)
        from payment.mock_adapter import MockAdapter
        assert isinstance(adapter, MockAdapter)

    def test_factory_raises_for_unknown_provider(self):
        import pytest
        from payment import PaymentProviderFactory
        with pytest.raises(ValueError, match="Unknown provider"):
            PaymentProviderFactory.get("unknown")


class TestMockAdapter:

    def test_create_merchant_returns_simulated_result(self):
        from payment.mock_adapter import MockAdapter
        from unittest.mock import MagicMock

        adapter = MockAdapter()
        application = MagicMock()
        application.id = 42
        application.merchant_id = 7

        result = adapter.create_merchant(application, channel=None)

        assert result.status == "approved"
        assert result.provider_application_id == "MOCK-APP-42"
        assert result.external_merchant_no == "MOCK-MER-7"
        assert result.raw_response.get("is_simulated") is True

    def test_create_transaction_returns_simulated_success(self):
        from payment.mock_adapter import MockAdapter
        from payment.base import TransactionPayload

        adapter = MockAdapter()
        payload = TransactionPayload(
            merchant_no="M-001",
            card_id=5,
            amount="100.50",
            idempotency_key="idem-abc",
            purpose="test payment",
        )

        result = adapter.create_transaction(payload, channel=None)

        assert result.status == "success"
        assert result.provider_txn_id == "MOCK-TXN-idem-abc"
        assert result.amount_confirmed == "100.50"
        assert result.raw_response.get("is_simulated") is True


class TestLKLAdapter:

    def test_instantiate_without_errors(self):
        from payment.lkl_adapter import LKLAdapter
        adapter = LKLAdapter()
        assert adapter.test_mode is False

    def test_create_merchant_returns_result(self):
        from payment.lkl_adapter import LKLAdapter
        from unittest.mock import MagicMock

        adapter = LKLAdapter()
        application = MagicMock()
        application.id = 10

        result = adapter.create_merchant(application, channel=None)

        assert result.status == "pending"
        assert result.provider_application_id == "LKL-MOCK-10"
        assert "simulated" in result.raw_response


class TestHuifuAdapter:

    def test_instantiate_without_errors(self):
        from payment.huifu_adapter import HuifuAdapter
        adapter = HuifuAdapter()
        assert adapter.test_mode is False

    def test_create_merchant_returns_result(self):
        from payment.huifu_adapter import HuifuAdapter
        from unittest.mock import MagicMock

        adapter = HuifuAdapter()
        application = MagicMock()
        application.id = 10

        result = adapter.create_merchant(application, channel=None)

        assert result.status == "pending"
        assert result.provider_application_id == "HF-MOCK-10"
        assert "simulated" in result.raw_response
