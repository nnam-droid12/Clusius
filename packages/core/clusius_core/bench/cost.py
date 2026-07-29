"""Cost model: `$/1M tokens` derived from a live instance price and measured
throughput. Never hardcode a `$/hr` figure in a result — it's always a caller-supplied
config value, since cloud pricing changes over time."""

from __future__ import annotations


def cost_per_1m_tokens(price_per_hour: float, tokens_per_second: float) -> float:
    if price_per_hour < 0:
        raise ValueError("price_per_hour must be non-negative")
    if tokens_per_second <= 0:
        raise ValueError("tokens_per_second must be positive to derive a cost rate")

    price_per_second = price_per_hour / 3600
    seconds_per_1m_tokens = 1_000_000 / tokens_per_second
    return price_per_second * seconds_per_1m_tokens


def cost_reduction_pct(baseline_cost_per_1m: float, candidate_cost_per_1m: float) -> float:
    """Positive means the candidate is cheaper than the baseline."""
    if baseline_cost_per_1m <= 0:
        raise ValueError("baseline_cost_per_1m must be positive")
    return (1 - candidate_cost_per_1m / baseline_cost_per_1m) * 100
