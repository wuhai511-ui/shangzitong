from .base import AbstractPaymentAdapter, MerchantOnboardingResult, TransactionPayload, TransactionResult


class HuifuAdapter(AbstractPaymentAdapter):
    def create_merchant(self, application, channel) -> MerchantOnboardingResult:
        # TODO: Huifu API signature per Huifu developer doc v2.0
        # POST https://api.huifu.com/v2/merchant/register
        # Headers: Authorization with HMAC-SHA256 signature
        # Body: merchant info from application
        return MerchantOnboardingResult(
            status="pending",
            provider_application_id=f"HF-MOCK-{application.id}",
            raw_response={"provider": "huifu", "simulated": True},
        )

    def get_merchant_status(self, application, channel) -> MerchantOnboardingResult:
        # TODO: Huifu API signature per Huifu developer doc v2.0
        # GET https://api.huifu.com/v2/merchant/{application.provider_application_id}
        return MerchantOnboardingResult(
            status="pending",
            provider_application_id=application.provider_application_id,
            external_merchant_no=application.external_merchant_no,
            raw_response={"provider": "huifu", "simulated": True},
        )

    def create_transaction(self, payload: TransactionPayload, channel) -> TransactionResult:
        # TODO: Huifu API signature per Huifu developer doc v2.0
        # POST https://api.huifu.com/v2/transaction/pay
        return TransactionResult(
            status="pending",
            provider_txn_id=f"HF-TXN-{payload.idempotency_key}",
            amount_confirmed=payload.amount,
            raw_response={"provider": "huifu", "simulated": True},
        )

    def query_transaction(self, provider_txn_id: str, channel) -> TransactionResult:
        # TODO: Huifu API signature per Huifu developer doc v2.0
        # GET https://api.huifu.com/v2/transaction/{provider_txn_id}
        return TransactionResult(
            status="pending",
            provider_txn_id=provider_txn_id,
            raw_response={"provider": "huifu", "simulated": True},
        )
