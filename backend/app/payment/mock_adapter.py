from .base import AbstractPaymentAdapter, MerchantOnboardingResult, TransactionPayload, TransactionResult


class MockAdapter(AbstractPaymentAdapter):
    def __init__(self, test_mode: bool = False):
        super().__init__(test_mode=True)

    def create_merchant(self, application, channel) -> MerchantOnboardingResult:
        return MerchantOnboardingResult(
            status="approved",
            provider_application_id=f"MOCK-APP-{application.id}",
            external_merchant_no=f"MOCK-MER-{application.merchant_id}",
            raw_response={"provider": "mock", "is_simulated": True},
        )

    def get_merchant_status(self, application, channel) -> MerchantOnboardingResult:
        return MerchantOnboardingResult(
            status="approved",
            provider_application_id=application.provider_application_id,
            external_merchant_no=application.external_merchant_no,
            raw_response={"provider": "mock", "is_simulated": True},
        )

    def create_transaction(self, payload: TransactionPayload, channel) -> TransactionResult:
        return TransactionResult(
            status="success",
            provider_txn_id=f"MOCK-TXN-{payload.idempotency_key}",
            amount_confirmed=payload.amount,
            raw_response={"provider": "mock", "is_simulated": True},
        )

    def query_transaction(self, provider_txn_id: str, channel) -> TransactionResult:
        return TransactionResult(
            status="success",
            provider_txn_id=provider_txn_id,
            raw_response={"provider": "mock", "is_simulated": True},
        )
