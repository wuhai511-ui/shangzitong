"""
Core data types for the algorithm engine.

Pure dataclass definitions — no DB dependency.
"""
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class BillingCycle(Enum):
    CURRENT = "current"
    NEXT = "next"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class CardInfo:
    """Credit card as seen by the algorithm engine."""
    card_id: int
    bank_name: str
    credit_limit: Decimal
    temp_limit: Decimal = Decimal("0")
    used_limit: Decimal = Decimal("0")
    overpayment: Decimal = Decimal("0")
    bill_day: int = 1       # 1-28
    due_day: int = 1         # 1-31
    swipe_fee_rate: Decimal = Decimal("0.006")
    interest_rate: Decimal = Decimal("0.0005")
    min_payment_ratio: Decimal = Decimal("0.1")
    installment_amount: Decimal = Decimal("0")
    bill_day_inclusive: bool = False

    @property
    def avail_limit(self) -> Decimal:
        return self.credit_limit + self.temp_limit - self.used_limit + self.overpayment


@dataclass
class SettlementForecast:
    """Daily settlement prediction."""
    date: date
    amount: Decimal
    confidence: float
    arrival: date


@dataclass
class Purchase:
    """A planned or actual purchase."""
    purchase_id: Optional[int]
    purchase_date: date
    amount: Decimal
    description: str = ""


@dataclass
class CardRecommendation:
    """Single-card recommendation."""
    card: CardInfo
    optimal_date: date
    free_days: int
    swipe_cost: Decimal
    daily_cost: Decimal
    risk_weight: float
    repayment_date: date


@dataclass
class PlanResult:
    """Full recommendation plan for a purchase."""
    purchase: Purchase
    recommendations: list[CardRecommendation] = field(default_factory=list)
    multi_card_split: list[tuple[CardInfo, Decimal]] = field(default_factory=list)
    coverage_ratio: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    gap_amount: Decimal = Decimal("0")
    warnings: list[str] = field(default_factory=list)


@dataclass
class DailySchedule:
    """One day in the global schedule."""
    date: date
    cash_pool: Decimal
    settlements: list[Decimal] = field(default_factory=list)
    repayments: list[dict] = field(default_factory=list)
    purchases: list[dict] = field(default_factory=list)
    alerts: list[dict] = field(default_factory=list)
