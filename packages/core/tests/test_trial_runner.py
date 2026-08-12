from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from clusius_core.migrate import deploy
from clusius_core.models import BenchmarkResult, LatencyPercentiles, ThroughputMetrics
from clusius_core.tune import trial_runner as trial_runner_module
from clusius_core.tune.search_space import TrialConfig
from clusius_core.tune.trial_runner import (
    RemoteTrialContext,
    deploy_and_benchmark,
    make_trial_evaluator,
)


def _context(**overrides: Any) -> RemoteTrialContext:
    defaults: dict[str, Any] = dict(
        runner=object(),
        target_host="10.0.0.5",
        instance_type="c4a-standard-2",
        arch="aarch64",
        price_per_hour=0.1,
        commit_sha="abc123",
        model_hash="sha256:test",
        llamacpp_image_tag="clusius-llamacpp:latest",
        vllm_image_tag="clusius-vllm:latest",
        llamacpp_gguf_paths={"Q4_K_M": "/models/qwen-q4km.gguf"},
        vllm_model_ref="Qwen/Qwen2.5-7B-Instruct",
        prompts=["hello"],
        concurrency=1,
        accuracy_scores={("llamacpp", "Q4_K_M"): 0.93},
    )
    defaults.update(overrides)
    return RemoteTrialContext(**defaults)


def _trial_config(**overrides: Any) -> TrialConfig:
    defaults: dict[str, Any] = dict(
        backend="llamacpp",
        quant="Q4_K_M",
        threads=4,
        core_pinning=True,
        batch_size=8,
        kv_cache_precision="int8",
        context_length=4096,
    )
    defaults.update(overrides)
    return TrialConfig(**defaults)


def _fake_result(**overrides: Any) -> BenchmarkResult:
    defaults: dict[str, Any] = dict(
        run_id="trial-1",
        timestamp=datetime.now(UTC),
        commit_sha="abc123",
        model="/models/qwen-q4km.gguf",
        model_hash="sha256:test",
        backend="llamacpp",
        quant="Q4_K_M",
        instance_type="c4a-standard-2",
        arch="aarch64",
        price_per_hour=0.1,
        threads=4,
        concurrency=1,
        throughput=ThroughputMetrics(tokens_per_second=50.0, requests_per_second=1.0),
        latency_ms=LatencyPercentiles(ttft_p50=20.0, p50=100.0, p95=200.0, p99=250.0),
        cost_per_1m_tokens=2.0,
        accuracy_score=0.93,
    )
    defaults.update(overrides)
    return BenchmarkResult(**defaults)


async def test_deploy_and_benchmark_starts_server_waits_and_benchmarks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_start_llamacpp(
        runner: Any, image_tag: Any, model_path: Any, config: Any, port: Any
    ) -> None:
        calls.append("start")
        assert model_path == "/models/qwen-q4km.gguf"

    async def fake_wait_for_health(url: Any, **kwargs: Any) -> None:
        calls.append("health")
        assert url == "http://10.0.0.5:8080"

    async def fake_run_benchmark(bench_config: Any) -> tuple[Any, list[Any], list[Any]]:
        calls.append("benchmark")
        assert bench_config.base_url == "http://10.0.0.5:8080/v1"
        assert bench_config.accuracy_score == 0.93
        return _fake_result(), [], []

    def fake_stop(runner: Any) -> None:
        calls.append("stop")

    monkeypatch.setattr(deploy, "start_llamacpp_server", fake_start_llamacpp)
    monkeypatch.setattr(deploy, "wait_for_health", fake_wait_for_health)
    monkeypatch.setattr(deploy, "stop_server", fake_stop)
    monkeypatch.setattr(trial_runner_module, "run_benchmark", fake_run_benchmark)

    result = await deploy_and_benchmark(_context(), _trial_config())

    assert calls == ["start", "health", "benchmark", "stop"]
    assert result.throughput.tokens_per_second == 50.0


async def test_deploy_and_benchmark_stops_server_even_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stopped = []

    def fake_start_llamacpp(
        runner: Any, image_tag: Any, model_path: Any, config: Any, port: Any
    ) -> None:
        pass

    async def fake_wait_for_health(url: Any, **kwargs: Any) -> None:
        raise TimeoutError("never came up")

    def fake_stop(runner: Any) -> None:
        stopped.append(True)

    monkeypatch.setattr(deploy, "start_llamacpp_server", fake_start_llamacpp)
    monkeypatch.setattr(deploy, "wait_for_health", fake_wait_for_health)
    monkeypatch.setattr(deploy, "stop_server", fake_stop)

    with pytest.raises(TimeoutError):
        await deploy_and_benchmark(_context(), _trial_config())

    assert stopped == [True]


async def test_deploy_and_benchmark_raises_on_missing_accuracy_score(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(deploy, "start_llamacpp_server", lambda *a, **k: None)
    monkeypatch.setattr(deploy, "wait_for_health", lambda *a, **k: _async_none())
    monkeypatch.setattr(deploy, "stop_server", lambda runner: None)

    config = _trial_config(quant="Q8_0")  # not in the context's accuracy_scores map

    with pytest.raises(KeyError):
        await deploy_and_benchmark(_context(), config)


async def test_deploy_and_benchmark_raises_when_requests_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_run_benchmark(bench_config: Any) -> tuple[Any, list[Any], list[Any]]:
        return _fake_result(), [], ["some failure"]

    monkeypatch.setattr(deploy, "start_llamacpp_server", lambda *a, **k: None)
    monkeypatch.setattr(deploy, "wait_for_health", lambda *a, **k: _async_none())
    monkeypatch.setattr(deploy, "stop_server", lambda runner: None)
    monkeypatch.setattr(trial_runner_module, "run_benchmark", fake_run_benchmark)

    with pytest.raises(RuntimeError, match="requests failed"):
        await deploy_and_benchmark(_context(), _trial_config())


def test_make_trial_evaluator_runs_synchronously(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_deploy_and_benchmark(ctx: Any, config: Any) -> BenchmarkResult:
        return _fake_result()

    monkeypatch.setattr(trial_runner_module, "deploy_and_benchmark", fake_deploy_and_benchmark)

    evaluate = make_trial_evaluator(_context())
    result = evaluate(_trial_config())

    assert isinstance(result, BenchmarkResult)


async def _async_none() -> None:
    return None
