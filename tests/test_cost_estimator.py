"""Tests for cost estimation."""

from placebot.core.cost_estimator import CostEstimator


def _model(input_per_m=0.25, output_per_m=1.25, name="Test Model"):
    return {
        "name": name,
        "input_cost_per_million": input_per_m,
        "output_cost_per_million": output_per_m,
    }


def test_estimate_cost_scales_with_records():
    small = CostEstimator.estimate_cost(10, _model(), "realtime", with_caching=False)
    large = CostEstimator.estimate_cost(1000, _model(), "realtime", with_caching=False)
    assert large["estimated_cost"] > small["estimated_cost"]
    assert small["num_records"] == 10


def test_caching_reduces_cost():
    cached = CostEstimator.estimate_cost(100, _model(), "realtime", with_caching=True)
    uncached = CostEstimator.estimate_cost(
        100, _model(), "realtime", with_caching=False
    )
    assert cached["estimated_cost"] < uncached["estimated_cost"]
    assert cached["savings_percentage"] > 0


def test_batch_mode_is_cheaper_than_realtime():
    realtime = CostEstimator.estimate_cost(
        100, _model(), "realtime", with_caching=False
    )
    batch = CostEstimator.estimate_cost(100, _model(), "batch", with_caching=False)
    assert batch["estimated_cost"] < realtime["estimated_cost"]


def test_zero_records_does_not_divide_by_zero():
    est = CostEstimator.estimate_cost(0, _model(), "realtime")
    assert est["cost_per_record"] == 0
    assert est["estimated_cost"] == 0
