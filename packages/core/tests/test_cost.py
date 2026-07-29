import pytest

from clusius_core.bench.cost import cost_per_1m_tokens, cost_reduction_pct


def test_cost_per_1m_tokens_basic() -> None:
    # $3.60/hr = $0.001/s; at 100 tok/s, 1M tokens takes 10,000s -> $10.00
    cost = cost_per_1m_tokens(price_per_hour=3.6, tokens_per_second=100)

    assert cost == pytest.approx(10.0)


def test_cost_per_1m_tokens_scales_inversely_with_throughput() -> None:
    slow = cost_per_1m_tokens(price_per_hour=3.6, tokens_per_second=50)
    fast = cost_per_1m_tokens(price_per_hour=3.6, tokens_per_second=100)

    assert slow == pytest.approx(fast * 2)


def test_cost_per_1m_tokens_rejects_non_positive_throughput() -> None:
    with pytest.raises(ValueError):
        cost_per_1m_tokens(price_per_hour=3.6, tokens_per_second=0)


def test_cost_reduction_pct_positive_when_cheaper() -> None:
    pct = cost_reduction_pct(baseline_cost_per_1m=10.0, candidate_cost_per_1m=6.0)

    assert pct == pytest.approx(40.0)


def test_cost_reduction_pct_negative_when_more_expensive() -> None:
    pct = cost_reduction_pct(baseline_cost_per_1m=10.0, candidate_cost_per_1m=12.0)

    assert pct == pytest.approx(-20.0)
