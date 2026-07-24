from .base import AbstractPaymentAdapter, MerchantOnboardingResult, TransactionPayload, TransactionResult


class LKLAdapter(AbstractPaymentAdapter):
    def create_merchant(self, application, channel) -> MerchantOnboardingResult:
        # TODO: LKL API signature per LKL developer doc v3.0
        # POST https://api.lkl.com/v3/merchant/apply
        # Headers: Authorization with RSA-SHA256 signature
        # Body: merchant info from application
        return MerchantOnboardingResult(
            status="pending",
            provider_application_id=f"LKL-MOCK-{application.id}",
            raw_response={"provider": "lkl", "simulated": True},
        )

    def get_merchant_status(self, application, channel) -> MerchantOnboardingResult:
        # TODO: LKL API signature per LKL developer doc v3.0
        # GET https://api.lkl.com/v3/merchant/{application.provider_application_id}
        return MerchantOnboardingResult(
            status="pending",
            provider_application_id=application.provider_application_id,
            external_merchant_no=application.external_merchant_no,
            raw_response={"provider": "lkl", "simulated": True},
        )

    def create_transaction(self, payload: TransactionPayload, channel) -> TransactionResult:
        # TODO: LKL API signature per LKL developer doc v3.0
        # POST https://api.lkl.com/v3/transaction/pay
        return TransactionResult(
            status="pending",
            provider_txn_id=f"LKL-TXN-{payload.idempotency_key}",
            amount_confirmed=payload.amount,
            raw_response={"provider": "lkl", "simulated": True},
        )

    def query_transaction(self, provider_txn_id: str, channel) -> TransactionResult:
        # TODO: LKL API signature per LKL developer doc v3.0
        # GET https://api.lkl.com/v3/transaction/{provider_txn_id}
        return TransactionResult(
            status="pending",
            provider_txn_id=provider_txn_id,
            raw_response={"provider": "lkl", "simulated": True},
        )
