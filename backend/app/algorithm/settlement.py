"""
Settlement arrival prediction using weighted weekly-average method.

MVP: simple weighted average of same-weekday settlements over past 4 weeks.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional
from .models import SettlementForecast


# Weights: most recent week = 0.4, oldest = 0.1
WEEK_WEIGHTS = [0.4, 0.3, 0.2, 0.1]
EPSILON = Decimal("0.01")


def predict_daily_settlement(
    target_date: date,
    history: dict[date, Decimal]
) -> SettlementForecast:
    """
    Predict settlement amount for target_date using 4-week weighted average.

    Args:
        target_date: date to predict
        history: dict of {date: amount} for past 30+ days

    Returns:
        SettlementForecast with predicted amount, confidence, and arrival date
    """
    amounts: list[Decimal] = []

    for week_offset in [7, 14, 21, 28]:
        hist_date = target_date - timedelta(days=week_offset)
        if hist_date in history:
            amounts.append(history[hist_date])

    if not amounts:
        return SettlementForecast(
            date=target_date,
            amount=Decimal("0"),
            confidence=0.0,
            arrival=_calc_arrival(target_date)
        )

    # Weighted average — weights align with actual data points
    weighted_sum = Decimal("0")
    for i, amt in enumerate(amounts):
        w = Decimal(str(WEEK_WEIGHTS[-(len(amounts) - i)]))  # align from end
        weighted_sum += amt * w

    total_weight = Decimal(str(sum(WEEK_WEIGHTS[-len(amounts):])))
    predicted = weighted_sum / total_weight if total_weight > 0 else Decimal("0")

    # Confidence: max(0, 1 - std_dev / (mean + epsilon))
    mean_val = sum(amounts, Decimal("0")) / len(amounts)
    if mean_val < EPSILON * 10:
        confidence = 0.3
    else:
        variance = sum((a - mean_val) ** 2 for a in amounts) / len(amounts)
        std_dev = variance.sqrt() if hasattr(variance, 'sqrt') else Decimal(str(float(variance) ** 0.5))
        confidence = max(0.0, 1.0 - float(std_dev / (mean_val + EPSILON)))

    return SettlementForecast(
        date=target_date,
        amount=predicted,
        confidence=round(confidence, 2),
        arrival=_calc_arrival(target_date)
    )


def _calc_arrival(trade_date: date) -> date:
    """Calculate actual arrival date: T+1, skip weekends."""
    arrival = trade_date + timedelta(days=1)
    while arrival.weekday() >= 5:  # Saturday=5, Sunday=6
        arrival += timedelta(days=1)
    return arrival


def build_forecast(
    today: date,
    history: dict[date, Decimal],
    days: int = 30
) -> list[SettlementForecast]:
    """Build settlement forecast for the next `days` days."""
    forecasts = []
    for i in range(1, days + 1):
        target = today + timedelta(days=i)
        forecasts.append(predict_daily_settlement(target, history))
    return forecasts
