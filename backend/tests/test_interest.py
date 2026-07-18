"""
Tests for interest-free period calculation (calendar mapping method).
"""
import sys
sys.path.insert(0, '/home/admin/szt/backend/app')

from datetime import date
from decimal import Decimal
from algorithm.models import CardInfo
from algorithm.interest import calc_interest_free_days, find_optimal_swipe_date


def test_basic_case():
    """Card: bill=5, due=25. Swipe on Jan 6 → next bill Feb 5, due Feb 25 = 50 days."""
    card = CardInfo(
        card_id=1, bank_name="招商银行",
        credit_limit=Decimal("50000"), used_limit=Decimal("10000"),
        bill_day=5, due_day=25
    )
    free_days, repay_date, cycle = calc_interest_free_days(card, date(2026, 1, 6))
    assert free_days == 50, f"Expected 50, got {free_days}"
    assert repay_date == date(2026, 2, 25), f"Expected 2026-02-25, got {repay_date}"
    print(f"PASS: basic_case — {free_days} days, repay {repay_date}")


def test_cross_month_due():
    """Card: bill=28, due=15. Swipe Feb 25 → Feb 28 bill → due Mar 15 = 18 days."""
    card = CardInfo(
        card_id=2, bank_name="工商银行",
        credit_limit=Decimal("100000"), used_limit=Decimal("0"),
        bill_day=28, due_day=15
    )
    free_days, repay_date, cycle = calc_interest_free_days(card, date(2026, 2, 25))
    # Feb 25 <= Feb 28 → current cycle → bill Feb 28, due Mar 15
    # Feb 25 to Mar 15 = (28-25) + 15 = 18
    assert free_days == 18, f"Expected 18, got {free_days}"
    assert repay_date == date(2026, 3, 15), f"Expected 2026-03-15, got {repay_date}"
    print(f"PASS: cross_month_due — {free_days} days, repay {repay_date}")


def test_end_of_month_bill():
    """Card: bill=31 (clamped to month end), due=10. Swipe Mar 1 → Apr 30 bill → due May 10."""
    card = CardInfo(
        card_id=3, bank_name="建设银行",
        credit_limit=Decimal("80000"), used_limit=Decimal("20000"),
        bill_day=31, due_day=10
    )
    free_days, repay_date, cycle = calc_interest_free_days(card, date(2026, 3, 1))
    # Mar 1 > Feb 28 (bill_day=31 clamped to 28 for Feb) → NEXT cycle
    # Containing bill: Mar 31, due_day(10) < bill_day(31) → repay Apr 10
    # Mar 1 to Apr 10 = 31-1 + 10 = 40
    assert repay_date == date(2026, 4, 10), f"Expected 2026-04-10, got {repay_date}"
    print(f"PASS: end_of_month_bill — {free_days} days, repay {repay_date}")


def test_optimal_swipe_date():
    """Purchase on Jan 4, bill=5 → wait 2 days to Jan 6 for +25 free days."""
    card = CardInfo(
        card_id=1, bank_name="招商银行",
        credit_limit=Decimal("50000"), used_limit=Decimal("10000"),
        bill_day=5, due_day=25
    )
    optimal_date, free_days, repay_date = find_optimal_swipe_date(
        card, date(2026, 1, 4)
    )
    # wait_days = 2, free_days difference >= 20 → recommend waiting
    assert optimal_date == date(2026, 1, 6), f"Expected Jan 6, got {optimal_date}"
    assert free_days == 50  # Jan 6 to Feb 25
    print(f"PASS: optimal_swipe_date — swipe {optimal_date}, {free_days} days")


def test_no_wait_needed():
    """Purchase on Jan 6 (already past bill=5) → swipe immediately."""
    card = CardInfo(
        card_id=1, bank_name="招商银行",
        credit_limit=Decimal("50000"), used_limit=Decimal("10000"),
        bill_day=5, due_day=25
    )
    optimal_date, free_days, repay_date = find_optimal_swipe_date(
        card, date(2026, 1, 6)
    )
    assert optimal_date == date(2026, 1, 6), f"Expected Jan 6, got {optimal_date}"
    print(f"PASS: no_wait_needed — swipe {optimal_date}, {free_days} days")


def test_wait_too_long():
    """Purchase on Jan 1, bill=5 → wait 4 days, too long → no recommendation to wait."""
    card = CardInfo(
        card_id=1, bank_name="招商银行",
        credit_limit=Decimal("50000"), used_limit=Decimal("10000"),
        bill_day=5, due_day=25
    )
    optimal_date, free_days, repay_date = find_optimal_swipe_date(
        card, date(2026, 1, 1)
    )
    # wait_days = 4 > 2 → should swipe immediately
    assert optimal_date == date(2026, 1, 1), f"Expected Jan 1, got {optimal_date}"
    print(f"PASS: wait_too_long — swipe {optimal_date}, {free_days} days")


if __name__ == "__main__":
    test_basic_case()
    test_cross_month_due()
    test_end_of_month_bill()
    test_optimal_swipe_date()
    test_no_wait_needed()
    test_wait_too_long()
    print("\n=== All interest.py tests passed ===")
