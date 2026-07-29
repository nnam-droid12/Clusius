import pytest

from clusius_core.bench.metrics import RequestMetric, aggregate, percentile


def test_percentile_nearest_rank() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0]

    assert percentile(values, 50) == 30.0
    assert percentile(values, 95) == 50.0
    assert percentile(values, 0) == 10.0
    assert percentile(values, 100) == 50.0


def test_percentile_rejects_empty_sample() -> None:
    with pytest.raises(ValueError):
        percentile([], 50)


def test_percentile_rejects_out_of_range_pct() -> None:
    with pytest.raises(ValueError):
        percentile([1.0], 150)


def test_aggregate_computes_throughput_and_latency() -> None:
    metrics = [
        RequestMetric(ttft_s=0.1, total_latency_s=1.0, completion_tokens=100, inter_token_latencies_s=[0.01, 0.02]),
        RequestMetric(ttft_s=0.2, total_latency_s=2.0, completion_tokens=200, inter_token_latencies_s=[0.03]),
    ]

    throughput, latency = aggregate(metrics, wall_clock_s=2.0)

    assert throughput.tokens_per_second == pytest.approx(150.0)
    assert throughput.requests_per_second == pytest.approx(1.0)
    assert latency.ttft_p50 == pytest.approx(150.0)  # nearest-rank of [100, 200] ms
    assert latency.p50 == pytest.approx(1000.0)
    assert latency.p95 == pytest.approx(2000.0)
    assert latency.inter_token_p50 is not None


def test_aggregate_rejects_empty_metrics() -> None:
    with pytest.raises(ValueError):
        aggregate([], wall_clock_s=1.0)


def test_aggregate_rejects_non_positive_wall_clock() -> None:
    metrics = [RequestMetric(ttft_s=0.1, total_latency_s=1.0, completion_tokens=10)]
    with pytest.raises(ValueError):
        aggregate(metrics, wall_clock_s=0)
