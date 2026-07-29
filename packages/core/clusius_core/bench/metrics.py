"""Per-request measurements and their aggregation into the percentile/throughput
summary that goes into a `BenchmarkResult`."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from clusius_core.models import LatencyPercentiles, ThroughputMetrics


@dataclass
class RequestMetric:
    """One completed request against an OpenAI-compatible endpoint."""

    ttft_s: float
    total_latency_s: float
    completion_tokens: int
    inter_token_latencies_s: list[float] = field(default_factory=list)


@dataclass
class RequestFailure:
    error: str


def percentile(values: list[float], pct: float) -> float:
    """Nearest-rank percentile over `values` (0 <= pct <= 100). No interpolation, so
    the reported figure is always an actually-observed measurement."""
    if not values:
        raise ValueError("cannot compute a percentile of an empty sample")
    if not 0 <= pct <= 100:
        raise ValueError("pct must be between 0 and 100")

    ordered = sorted(values)
    rank = math.ceil(pct / 100 * len(ordered)) - 1
    rank = min(max(rank, 0), len(ordered) - 1)
    return ordered[rank]


def aggregate(
    metrics: list[RequestMetric], wall_clock_s: float
) -> tuple[ThroughputMetrics, LatencyPercentiles]:
    if not metrics:
        raise ValueError("cannot aggregate an empty set of request metrics")
    if wall_clock_s <= 0:
        raise ValueError("wall_clock_s must be positive")

    total_tokens = sum(m.completion_tokens for m in metrics)
    throughput = ThroughputMetrics(
        tokens_per_second=total_tokens / wall_clock_s,
        requests_per_second=len(metrics) / wall_clock_s,
    )

    ttfts = [m.ttft_s * 1000 for m in metrics]
    latencies = [m.total_latency_s * 1000 for m in metrics]
    inter_token = [lat * 1000 for m in metrics for lat in m.inter_token_latencies_s]

    latency = LatencyPercentiles(
        ttft_p50=percentile(ttfts, 50),
        inter_token_p50=percentile(inter_token, 50) if inter_token else None,
        p50=percentile(latencies, 50),
        p95=percentile(latencies, 95),
        p99=percentile(latencies, 99),
    )

    return throughput, latency
