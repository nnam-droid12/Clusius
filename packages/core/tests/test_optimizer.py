from datetime import UTC, datetime

from clusius_core.models import BenchmarkResult, LatencyPercentiles, ThroughputMetrics
from clusius_core.tune.optimizer import TunerConfig, feasible_trials, pareto_frontier, run_search
from clusius_core.tune.search_space import SearchSpace, TrialConfig

# Deterministic synthetic accuracy/throughput/latency model per quant, so the test
# exercises the optimizer's constraint handling and Pareto logic without needing a
# real inference server. Q4_0 is deliberately below a 0.85 accuracy floor.
_ACCURACY_BY_QUANT = {"Q8_0": 0.97, "Q4_K_M": 0.92, "Q4_0": 0.80, "int8": 0.96, "int4": 0.88}
_THROUGHPUT_BASE_BY_QUANT = {"Q8_0": 20.0, "Q4_K_M": 35.0, "Q4_0": 50.0, "int8": 60.0, "int4": 90.0}


def _synthetic_evaluate(config: TrialConfig) -> BenchmarkResult:
    accuracy = _ACCURACY_BY_QUANT[config.quant]
    throughput = _THROUGHPUT_BASE_BY_QUANT[config.quant] * (config.threads / 8)
    # Higher throughput configs trade off some latency, and low-thread configs run
    # slower per-request even though this is a CPU-bound synthetic model.
    p95_latency_ms = 2000.0 * (8 / config.threads)
    cost = 1000.0 / throughput

    return BenchmarkResult(
        run_id=f"trial-{config.backend}-{config.quant}-{config.threads}",
        timestamp=datetime.now(UTC),
        commit_sha="deadbeef",
        model="qwen2.5-7b-instruct",
        model_hash="sha256:test",
        backend=config.backend,
        quant=config.quant,
        instance_type="c4a-standard-16",
        arch="aarch64",
        price_per_hour=0.5,
        threads=config.threads,
        core_pinning=config.core_pinning,
        batch_size=config.batch_size,
        kv_cache_precision=config.kv_cache_precision,
        context_length=config.context_length,
        concurrency=8,
        throughput=ThroughputMetrics(tokens_per_second=throughput, requests_per_second=1.0),
        latency_ms=LatencyPercentiles(
            ttft_p50=50.0,
            p50=p95_latency_ms * 0.6,
            p95=p95_latency_ms,
            p99=p95_latency_ms * 1.2,
        ),
        cost_per_1m_tokens=cost,
        accuracy_score=accuracy,
    )


def _space() -> SearchSpace:
    return SearchSpace(threads=[4, 8, 16], batch_sizes=[1, 8], context_lengths=[4096])


def test_run_search_executes_max_trials() -> None:
    config = TunerConfig(max_trials=15, accuracy_floor=0.85, latency_sla_ms=3000.0, seed=42)

    study = run_search(_space(), config, _synthetic_evaluate)

    assert len(study.trials) == 15


def test_infeasible_trials_are_excluded_from_pareto_frontier() -> None:
    config = TunerConfig(max_trials=25, accuracy_floor=0.85, latency_sla_ms=3000.0, seed=42)

    study = run_search(_space(), config, _synthetic_evaluate)

    frontier = pareto_frontier(study)
    assert frontier
    for trial in frontier:
        assert trial.user_attrs["accuracy_score"] >= 0.85
        assert trial.user_attrs["quant"] != "Q4_0"


def test_feasible_trials_all_satisfy_constraints() -> None:
    config = TunerConfig(max_trials=25, accuracy_floor=0.85, latency_sla_ms=1000.0, seed=7)

    study = run_search(_space(), config, _synthetic_evaluate)

    feasible = feasible_trials(study)
    for trial in feasible:
        assert trial.user_attrs["accuracy_score"] >= 0.85
        assert trial.user_attrs["p95_latency_ms"] <= 1000.0


def test_pareto_frontier_is_subset_of_feasible_trials() -> None:
    config = TunerConfig(max_trials=25, accuracy_floor=0.85, latency_sla_ms=3000.0, seed=3)

    study = run_search(_space(), config, _synthetic_evaluate)

    feasible_numbers = {t.number for t in feasible_trials(study)}
    frontier_numbers = {t.number for t in pareto_frontier(study)}
    assert frontier_numbers <= feasible_numbers
