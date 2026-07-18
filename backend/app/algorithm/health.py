"""经营健康评分模型 — P3A: Business health score model.

Calculates a composite health score (0-100) for credit card operations
based on four dimensions: interest-free day utilization, repayment punctuality,
funding stability, and credit limit health.
"""


def calculate_health_score(metrics: dict) -> dict:
    """Calculate a health score from operational metrics.

    Args:
        metrics: Dictionary with keys:
            - free_days_utilization (float, 0-1): Utilization rate of interest-free days
            - overdue_count (float, 0-1): Overdue rate
            - gap_frequency (float, 0-1): Funding gap frequency
            - card_utilization (float, 0-1): Credit limit utilization rate

    Returns:
        dict with score (0-100), grade, and per-dimension scores.
    """
    free_days_utilization = float(metrics.get("free_days_utilization", 0))
    overdue_count = float(metrics.get("overdue_count", 0))
    gap_frequency = float(metrics.get("gap_frequency", 0))
    card_utilization = float(metrics.get("card_utilization", 0))

    # Dimension scores (each 0-1)
    dim_free_days = free_days_utilization
    dim_repayment = 1.0 - overdue_count
    dim_stability = 1.0 - gap_frequency
    dim_health = 1.0 - card_utilization

    # Weighted composite: 免息期利用率 40% + 还款准时率 30% + 资金稳定性 20% + 额度健康度 10%
    score = (
        dim_free_days * 40
        + dim_repayment * 30
        + dim_stability * 20
        + dim_health * 10
    )

    # Clamp to [0, 100]
    score = max(0.0, min(100.0, score))

    # Grade
    if score >= 80:
        grade = "优秀"
    elif score >= 60:
        grade = "良好"
    elif score >= 40:
        grade = "一般"
    else:
        grade = "较差"

    return {
        "score": round(score, 1),
        "grade": grade,
        "dimensions": {
            "免息期利用率": round(dim_free_days * 100, 1),
            "还款准时率": round(dim_repayment * 100, 1),
            "资金稳定性": round(dim_stability * 100, 1),
            "额度健康度": round(dim_health * 100, 1),
        },
    }
