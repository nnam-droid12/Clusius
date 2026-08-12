from pathlib import Path
from typing import Any

from clusius_core.bench.charts import plot_cost_comparison, plot_pareto_frontier
from clusius_core.models import BenchmarkResult, LatencyPercentiles, ThroughputMetrics, utcnow


def _result(**overrides: Any) -> BenchmarkResult:
    defaults: dict[str, Any] = dict(
        run_id="r1",
        timestamp=utcnow(),
        commit_sha="abc123",
        model="qwen2.5-7b-instruct",
        model_hash="sha256:test",
        backend="llamacpp",
        quant="Q4_K_M",
        instance_type="c4a-standard-16",
        arch="aarch64",
        price_per_hour=0.5,
        threads=16,
        concurrency=4,
        throughput=ThroughputMetrics(tokens_per_second=80.0, requests_per_second=2.0),
        latency_ms=LatencyPercentiles(ttft_p50=50.0, p50=400.0, p95=700.0, p99=900.0),
        cost_per_1m_tokens=1.5,
        accuracy_score=0.95,
    )
    defaults.update(overrides)
    return BenchmarkResult(**defaults)


def test_plot_pareto_frontier_writes_png(tmp_path: Path) -> None:
    trials = [
        {"tokens_per_second": 40.0, "cost_per_1m_tokens": 3.0, "feasible": True},
        {"tokens_per_second": 80.0, "cost_per_1m_tokens": 1.5, "feasible": True},
        {"tokens_per_second": 120.0, "cost_per_1m_tokens": 1.0, "feasible": False},
    ]
    out_path = tmp_path / "pareto.png"

    result = plot_pareto_frontier(trials, out_path, winner_index=1)

    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_plot_pareto_frontier_handles_all_infeasible(tmp_path: Path) -> None:
    trials = [{"tokens_per_second": 40.0, "cost_per_1m_tokens": 3.0, "feasible": False}]
    out_path = tmp_path / "pareto.png"

    plot_pareto_frontier(trials, out_path)

    assert out_path.exists()


def test_plot_cost_comparison_writes_png(tmp_path: Path) -> None:
    baseline = _result(arch="x86_64", instance_type="c4-standard-16", cost_per_1m_tokens=4.0)
    winner = _result(cost_per_1m_tokens=1.5)
    out_path = tmp_path / "cost.png"

    result = plot_cost_comparison(baseline, winner, out_path)

    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0
