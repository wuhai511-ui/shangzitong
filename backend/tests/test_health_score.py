"""RED: Tests for 经营健康评分模型 (P3A)."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))


class TestHealthScore:
    """Test the health score calculation algorithm."""

    def test_score_range(self):
        """Score should always be between 0 and 100."""
        from algorithm.health import calculate_health_score

        # Test with mid-range inputs
        result = calculate_health_score({
            "free_days_utilization": 0.5,
            "overdue_count": 0.3,
            "gap_frequency": 0.2,
            "card_utilization": 0.4,
        })
        assert 0 <= result["score"] <= 100

    def test_perfect_score(self):
        """Perfect metrics should yield a high score (80+)."""
        from algorithm.health import calculate_health_score

        result = calculate_health_score({
            "free_days_utilization": 1.0,
            "overdue_count": 0.0,
            "gap_frequency": 0.0,
            "card_utilization": 0.0,
        })
        assert result["score"] >= 80
        assert "grade" in result
        assert "dimensions" in result
        # Dimensions should be in Chinese
        assert "免息期利用率" in result["dimensions"]
        assert "还款准时率" in result["dimensions"]
        assert "资金稳定性" in result["dimensions"]
        assert "额度健康度" in result["dimensions"]

    def test_poor_score(self):
        """Poor metrics should yield a low score (<40)."""
        from algorithm.health import calculate_health_score

        result = calculate_health_score({
            "free_days_utilization": 0.0,
            "overdue_count": 1.0,
            "gap_frequency": 1.0,
            "card_utilization": 1.0,
        })
        assert result["score"] < 40
