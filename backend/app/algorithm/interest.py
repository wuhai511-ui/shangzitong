"""
Interest-free period calculation using calendar mapping.

Replaces the error-prone `repayment_date = next_bill_date + (due_day - bill_day)`
with month+day direct lookup, avoiding cross-month arithmetic bugs.
"""
from calendar import monthrange
from datetime import date, timedelta
from .models import CardInfo, BillingCycle


def _month_bill_date(year: int, month: int, day: int) -> date:
    """Return the bill date in (year, month). If day exceeds month length, use last day."""
    max_day = monthrange(year, month)[1]
    actual_day = min(day, max_day)
    return date(year, month, actual_day)


def _next_month(year: int, month: int) -> tuple[int, int]:
    """Return (year, month) for the following month."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def calc_interest_free_days(
    card: CardInfo,
    trans_date: date
) -> tuple[int, date, BillingCycle]:
    """
    Calculate interest-free days for a transaction.

    Returns:
        (interest_free_days, repayment_date, billing_cycle)
    """
    bill_day = card.bill_day
    due_day = card.due_day

    # 1. Current month's bill date
    current_bill = _month_bill_date(trans_date.year, trans_date.month, bill_day)

    # 2. Determine which billing cycle the transaction falls into
    if trans_date > current_bill:
        billing_cycle = BillingCycle.NEXT
    elif trans_date == current_bill and card.bill_day_inclusive:
        billing_cycle = BillingCycle.NEXT
    else:
        billing_cycle = BillingCycle.CURRENT

    # 3. Find the bill date that contains this transaction
    if billing_cycle == BillingCycle.CURRENT:
        # Transaction on THIS month's bill
        bill_month_year = current_bill.year
        bill_month_month = current_bill.month
    else:
        # Transaction on NEXT month's bill
        bill_month_year, bill_month_month = _next_month(
            current_bill.year, current_bill.month
        )

    bill_containing = _month_bill_date(bill_month_year, bill_month_month, bill_day)

    # 4. Calculate repayment date from the containing bill
    if due_day < bill_day:
        # Cross-month repayment: bill in month M, due in month M+1
        repay_year, repay_month = _next_month(bill_month_year, bill_month_month)
    else:
        repay_year, repay_month = bill_month_year, bill_month_month

    repayment_date = _month_bill_date(repay_year, repay_month, due_day)

    # 5. Interest-free days
    free_days = (repayment_date - trans_date).days

    return free_days, repayment_date, billing_cycle


def find_optimal_swipe_date(
    card: CardInfo,
    purchase_date: date
) -> tuple[date, int, date]:
    """
    Find the best swipe date near the purchase date for maximum interest-free period.

    If waiting <= 2 days yields >= 20 extra free days, recommend waiting.
    Otherwise, swipe immediately.

    Returns:
        (optimal_swipe_date, interest_free_days, repayment_date)
    """
    bill_day = card.bill_day
    current_bill = _month_bill_date(purchase_date.year, purchase_date.month, bill_day)

    if purchase_date > current_bill:
        # Already past bill day — swipe now
        free_days, repay_date, _ = calc_interest_free_days(card, purchase_date)
        return purchase_date, free_days, repay_date

    # Before bill day — evaluate waiting
    wait_until = current_bill + timedelta(days=1)
    wait_days = (wait_until - purchase_date).days

    free_days_now, repay_now, _ = calc_interest_free_days(card, purchase_date)
    free_days_wait, repay_wait, _ = calc_interest_free_days(card, wait_until)

    if wait_days <= 2 and (free_days_wait - free_days_now) >= 20:
        return wait_until, free_days_wait, repay_wait

    return purchase_date, free_days_now, repay_now
