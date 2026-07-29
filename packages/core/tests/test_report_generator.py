from pathlib import Path

from clusius_core.analyze.scanner import Finding
from clusius_core.models import BenchmarkResult, LatencyPercentiles, ThroughputMetrics, utcnow
from clusius_core.report.generator import (
    MigrationReportInputs,
    render_migration_report,
    write_migration_report,
)
from clusius_core.tune.search_space import TrialConfig


def _result(**overrides) -> BenchmarkResult:
    defaults = dict(
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


def _inputs(**overrides) -> MigrationReportInputs:
    baseline = _result(
        arch="x86_64",
        instance_type="c4-standard-16",
        backend="llamacpp",
        quant="fp16",
        throughput=ThroughputMetrics(tokens_per_second=40.0, requests_per_second=1.0),
        latency_ms=LatencyPercentiles(ttft_p50=80.0, p50=800.0, p95=1200.0, p99=1500.0),
        cost_per_1m_tokens=4.0,
        accuracy_score=0.96,
    )
    winner = _result()
    winner_config = TrialConfig(
        backend="llamacpp",
        quant="Q4_K_M",
        threads=16,
        core_pinning=True,
        batch_size=8,
        kv_cache_precision="int8",
        context_length=4096,
    )
    defaults = dict(
        workload_name="showcase-agent",
        model_ref="qwen2.5-7b-instruct",
        commit_sha="abc123",
        baseline=baseline,
        winner=winner,
        winner_config=winner_config,
        backend_justification=(
            "Selected llama.cpp+KleidiAI: it delivered the best throughput at equal accuracy."
        ),
        accuracy_floor=0.9,
        latency_sla_ms=1000.0,
        search_trial_count=25,
        analysis_blockers=[
            Finding(
                severity="blocker",
                category="cuda",
                file="Dockerfile",
                line=1,
                message="CUDA base image has no Arm64 build",
            )
        ],
        optimizations_applied=[
            "KleidiAI kernels linked",
            "Q4_K_M quantization",
            "16 threads, core pinning on",
        ],
    )
    defaults.update(overrides)
    return MigrationReportInputs(**defaults)


def test_render_includes_baseline_and_winner_numbers() -> None:
    report = render_migration_report(_inputs())

    assert "c4-standard-16" in report
    assert "c4a-standard-16" in report
    assert "40.0 tok/s" in report  # baseline section
    assert "| 80.0 |" in report  # winner throughput in the results table


def test_render_computes_correct_cost_delta() -> None:
    report = render_migration_report(_inputs())

    # cost went from 4.0 to 1.5 -> (1.5-4.0)/4.0*100 = -62.5%
    assert "-62.5%" in report


def test_render_computes_correct_throughput_delta() -> None:
    report = render_migration_report(_inputs())

    # throughput went from 40.0 to 80.0 -> +100.0%
    assert "+100.0%" in report


def test_render_includes_analysis_blockers() -> None:
    report = render_migration_report(_inputs())

    assert "cuda" in report
    assert "CUDA base image has no Arm64 build" in report


def test_render_handles_no_blockers() -> None:
    report = render_migration_report(_inputs(analysis_blockers=[]))

    assert "No x86-only blockers were found" in report


def test_render_includes_backend_justification() -> None:
    report = render_migration_report(_inputs())

    assert "Selected llama.cpp+KleidiAI" in report


def test_write_migration_report_creates_file(tmp_path: Path) -> None:
    path = write_migration_report(_inputs(), tmp_path)

    assert path.name == "MIGRATION_REPORT.md"
    assert path.exists()
    assert "showcase-agent" in path.read_text(encoding="utf-8")
