"""
Bank risk-control checks for credit card transaction recommendations.
"""
from datetime import date
from decimal import Decimal
from .models import CardInfo


def risk_check(card: CardInfo, amount: Decimal, trans_date: date) -> bool:
    """
    Check if a transaction triggers bank risk-control rules.

    Returns True if the transaction passes all checks.
    Returns False if ANY rule is triggered (card is downgraded, not rejected).
    """
    # Rule 1: Round integer amount >= 10000 → suspicious
    if amount >= 10000 and amount % 1 == 0:
        return False

    # Rule 2: Utilization rate > 85%
    if card.avail_limit > 0:
        util_rate = float(amount / card.avail_limit)
        if util_rate > 0.85:
            return False

    # Rule 3: Large amount on bill_day + 1 → bank-sensitive
    current_month_bill = date(trans_date.year, trans_date.month, min(card.bill_day, 28))
    if trans_date == date(trans_date.year, trans_date.month, min(card.bill_day, 28)) + __import__('datetime').timedelta(days=1):
        if amount >= 5000:
            return False

    return True


def apply_utilization_cap(card: CardInfo, cap: float = 0.85) -> Decimal:
    """Return the max usable amount under the utilization cap."""
    return card.avail_limit * Decimal(str(cap))
