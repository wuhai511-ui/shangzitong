from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class MerchantOnboardingResult:
    status: str = "pending"
    provider_application_id: str | None = None
    external_merchant_no: str | None = None
    raw_response: dict = field(default_factory=dict)


@dataclass
class TransactionPayload:
    merchant_no: str = ""
    card_id: int = 0
    amount: str = "0.00"
    idempotency_key: str = ""
    purpose: str = ""


@dataclass
class TransactionResult:
    status: str = "pending"
    provider_txn_id: str | None = None
    amount_confirmed: str | None = None
    raw_response: dict = field(default_factory=dict)


class AbstractPaymentAdapter(ABC):
    def __init__(self, test_mode: bool = False):
        self.test_mode = test_mode

    @abstractmethod
    def create_merchant(self, application, channel) -> MerchantOnboardingResult: ...

    @abstractmethod
    def get_merchant_status(self, application, channel) -> MerchantOnboardingResult: ...

    @abstractmethod
    def create_transaction(self, payload: TransactionPayload, channel) -> TransactionResult: ...

    @abstractmethod
    def query_transaction(self, provider_txn_id: str, channel) -> TransactionResult: ...
