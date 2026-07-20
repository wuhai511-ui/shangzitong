"""Business health score calculated from available measured dimensions."""


def calculate_health_score(metrics: dict) -> dict:
    """Calculate a normalized 0-100 score from measured operational metrics."""
    free_days_utilization = float(metrics.get("free_days_utilization", 0))
    overdue_count = metrics.get("overdue_count")
    gap_frequency = float(metrics.get("gap_frequency", 0))
    card_utilization = float(metrics.get("card_utilization", 0))

    weighted_dimensions = [
        ("免息期利用率", free_days_utilization, 0.4),
    ]
    if overdue_count is not None:
        weighted_dimensions.append(
            ("还款准时率", 1.0 - float(overdue_count), 0.3)
        )
    weighted_dimensions.extend(
        [
            ("资金稳定性", 1.0 - gap_frequency, 0.2),
            ("额度健康度", 1.0 - card_utilization, 0.1),
        ]
    )

    included_weight = sum(weight for _, _, weight in weighted_dimensions)
    score = (
        sum(value * weight for _, value, weight in weighted_dimensions)
        / included_weight
        * 100
    )
    score = max(0.0, min(100.0, score))

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
            name: round(value * 100, 1)
            for name, value, _ in weighted_dimensions
        },
    }
