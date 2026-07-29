import pytest
from clusius_core.tune.backend_selector import BackendProbeResult, select_backend


def test_selects_higher_throughput_when_both_eligible() -> None:
    probes = [
        BackendProbeResult(
            backend="llamacpp",
            concurrency=1,
            tokens_per_second=40.0,
            p95_latency_ms=500.0,
            ttft_p50_ms=50.0,
            accuracy_score=0.95,
            cost_per_1m_tokens=3.0,
        ),
        BackendProbeResult(
            backend="vllm",
            concurrency=32,
            tokens_per_second=180.0,
            p95_latency_ms=800.0,
            ttft_p50_ms=200.0,
            accuracy_score=0.94,
            cost_per_1m_tokens=1.2,
        ),
    ]

    selection = select_backend(probes, accuracy_floor=0.9, latency_sla_ms=1000.0)

    assert selection.backend == "vllm"
    assert "vLLM+ACL" in selection.justification
    assert "llama.cpp+KleidiAI" in selection.justification


def test_excludes_backend_below_accuracy_floor() -> None:
    probes = [
        BackendProbeResult(
            backend="llamacpp",
            concurrency=1,
            tokens_per_second=200.0,
            p95_latency_ms=500.0,
            ttft_p50_ms=50.0,
            accuracy_score=0.60,
            cost_per_1m_tokens=1.0,
        ),
        BackendProbeResult(
            backend="vllm",
            concurrency=32,
            tokens_per_second=100.0,
            p95_latency_ms=800.0,
            ttft_p50_ms=200.0,
            accuracy_score=0.94,
            cost_per_1m_tokens=1.5,
        ),
    ]

    selection = select_backend(probes, accuracy_floor=0.9, latency_sla_ms=1000.0)

    assert selection.backend == "vllm"
    assert "excluded" in selection.justification
    assert "accuracy" in selection.justification


def test_excludes_backend_above_latency_sla() -> None:
    probes = [
        BackendProbeResult(
            backend="llamacpp",
            concurrency=1,
            tokens_per_second=40.0,
            p95_latency_ms=500.0,
            ttft_p50_ms=50.0,
            accuracy_score=0.95,
            cost_per_1m_tokens=3.0,
        ),
        BackendProbeResult(
            backend="vllm",
            concurrency=64,
            tokens_per_second=300.0,
            p95_latency_ms=5000.0,
            ttft_p50_ms=200.0,
            accuracy_score=0.94,
            cost_per_1m_tokens=0.8,
        ),
    ]

    selection = select_backend(probes, accuracy_floor=0.9, latency_sla_ms=1000.0)

    assert selection.backend == "llamacpp"
    assert "excluded" in selection.justification
    assert "latency" in selection.justification


def test_raises_when_no_backend_is_eligible() -> None:
    probes = [
        BackendProbeResult(
            backend="llamacpp",
            concurrency=1,
            tokens_per_second=40.0,
            p95_latency_ms=5000.0,
            ttft_p50_ms=50.0,
            accuracy_score=0.5,
            cost_per_1m_tokens=3.0,
        ),
    ]

    with pytest.raises(RuntimeError):
        select_backend(probes, accuracy_floor=0.9, latency_sla_ms=1000.0)


def test_raises_on_empty_probe_list() -> None:
    with pytest.raises(ValueError):
        select_backend([], accuracy_floor=0.9, latency_sla_ms=1000.0)
