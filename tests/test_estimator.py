"""Tests for the cost estimator."""

from estimator import CostEstimate, estimate_cost


class TestEstimateCost:
    def test_returns_cost_estimate(self):
        result = estimate_cost(total_population=7_500_000, target_count=5000)
        assert isinstance(result, CostEstimate)

    def test_target_preserved(self):
        result = estimate_cost(total_population=1_000_000, target_count=3000)
        assert result.target_unique == 3000

    def test_cost_positive(self):
        result = estimate_cost(total_population=500_000, target_count=1000)
        assert result.estimated_cost_usd > 0

    def test_api_calls_positive(self):
        result = estimate_cost(total_population=500_000, target_count=1000)
        assert result.estimated_api_calls > 0

    def test_larger_target_higher_cost(self):
        small = estimate_cost(total_population=1_000_000, target_count=1000)
        large = estimate_cost(total_population=1_000_000, target_count=10000)
        assert large.estimated_cost_usd > small.estimated_cost_usd

    def test_within_free_tier_small_target(self):
        result = estimate_cost(total_population=500_000, target_count=1000)
        assert result.within_free_tier is True

    def test_time_estimate_positive(self):
        result = estimate_cost(total_population=500_000, target_count=1000)
        assert result.estimated_time_minutes > 0
