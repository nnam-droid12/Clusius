from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from clusius_core.migrate import deploy, model_prep
from clusius_core.migrate.ssh_runner import TargetHost
from clusius_core.models import BenchmarkResult, LatencyPercentiles, ThroughputMetrics
from clusius_core.pipeline import PipelineConfig, run_full_pipeline
from clusius_core.tune import trial_runner as trial_runner_module

# Deterministic synthetic model: accuracy always passes, throughput scales with
# threads, so the search has a clear winner and the constraint machinery is real.
_ACCURACY = 0.95


async def _fake_deploy_and_benchmark(ctx, config) -> BenchmarkResult:
    throughput = 20.0 * config.threads
    return BenchmarkResult(
        run_id=f"trial-{config.threads}-{config.quant}",
        timestamp=datetime.now(UTC),
        commit_sha="abc123",
        model=ctx.llamacpp_gguf_paths.get(config.quant, ctx.vllm_model_ref),
        model_hash=ctx.model_hash,
        backend=config.backend,
        quant=config.quant,
        instance_type=ctx.instance_type,
        arch=ctx.arch,
        price_per_hour=ctx.price_per_hour,
        threads=config.threads,
        core_pinning=config.core_pinning,
        batch_size=config.batch_size,
        kv_cache_precision=config.kv_cache_precision,
        context_length=config.context_length,
        concurrency=ctx.concurrency,
        throughput=ThroughputMetrics(tokens_per_second=throughput, requests_per_second=1.0),
        latency_ms=LatencyPercentiles(ttft_p50=10.0, p50=200.0, p95=400.0, p99=500.0),
        cost_per_1m_tokens=1000.0 / throughput,
        accuracy_score=_ACCURACY,
    )


@pytest.fixture(autouse=True)
def _patch_infra(monkeypatch: pytest.MonkeyPatch) -> dict[str, list]:
    calls: dict[str, list] = {
        "docker_installed": [],
        "images_built": [],
        "models_prepared": [],
    }

    def fake_docker_installed(runner):
        calls["docker_installed"].append(runner)

    monkeypatch.setattr(deploy, "ensure_docker_installed", fake_docker_installed)

    def fake_build_image(runner, dockerfile_path, tag, build_args=None):
        calls["images_built"].append((tag, build_args))

    monkeypatch.setattr(deploy, "build_backend_image", fake_build_image)

    def fake_prepare_models(runner, image_tag, hf_model_id, quant_types, workdir=None):
        calls["models_prepared"].append((image_tag, tuple(quant_types)))
        return {q: f"/models/{image_tag}-{q}.gguf" for q in quant_types}

    monkeypatch.setattr(model_prep, "prepare_gguf_models", fake_prepare_models)
    monkeypatch.setattr(trial_runner_module, "deploy_and_benchmark", _fake_deploy_and_benchmark)

    return calls


def _config(**overrides) -> PipelineConfig:
    defaults = dict(
        workload_name="showcase-agent",
        hf_model_id="Qwen/Qwen2.5-0.5B-Instruct",
        source_path=None,
        arm_target=TargetHost(host="10.0.0.1", user="clusius", price_per_hour=0.1),
        x86_target=TargetHost(host="10.0.0.2", user="clusius", price_per_hour=0.2),
        arm_instance_type="c4a-standard-2",
        x86_instance_type="c4-standard-2",
        sla_p95_latency_ms=1000.0,
        sla_accuracy_floor=0.9,
        search_budget_trials=6,
        commit_sha="abc123",
        prompts=["hello"],
        threads_options=[1, 2],
        quant_types=["Q4_K_M"],
        context_lengths=[2048],
        batch_sizes=[1],
    )
    defaults.update(overrides)
    return PipelineConfig(**defaults)


def test_run_full_pipeline_builds_both_images_with_kleidiai_toggle(_patch_infra: dict) -> None:
    run_full_pipeline(_config())

    assert _patch_infra["images_built"] == [
        ("clusius-llamacpp:arm", {"ENABLE_KLEIDIAI": "ON"}),
        ("clusius-llamacpp:x86", {"ENABLE_KLEIDIAI": "OFF"}),
    ]


def test_run_full_pipeline_prepares_models_on_both_targets(_patch_infra: dict) -> None:
    run_full_pipeline(_config())

    tags = {tag for tag, _ in _patch_infra["models_prepared"]}
    assert tags == {"clusius-llamacpp:arm", "clusius-llamacpp:x86"}


def test_run_full_pipeline_picks_higher_throughput_winner(_patch_infra: dict) -> None:
    result = run_full_pipeline(_config())

    # threads=2 always yields double the throughput of threads=1 in the synthetic model
    assert result.winner_config.threads == 2
    assert result.winner_result.throughput.tokens_per_second == pytest.approx(40.0)


def test_run_full_pipeline_benchmarks_baseline_on_x86_target(_patch_infra: dict) -> None:
    result = run_full_pipeline(_config())

    assert result.baseline_result.arch == "x86_64"
    assert result.baseline_result.instance_type == "c4-standard-2"
    # same winning config replayed on the baseline for a fair comparison
    assert result.baseline_result.threads == result.winner_config.threads


def test_run_full_pipeline_generates_a_report(_patch_infra: dict) -> None:
    result = run_full_pipeline(_config())

    assert "showcase-agent" in result.report_markdown
    assert "Qwen/Qwen2.5-0.5B-Instruct" in result.report_markdown
    assert "Selected" in result.backend_justification


def test_run_full_pipeline_records_trial_history(_patch_infra: dict) -> None:
    result = run_full_pipeline(_config(search_budget_trials=4))

    assert len(result.trials) == 4
    assert all(t.feasible for t in result.trials)  # synthetic model always passes SLA/accuracy


def test_run_full_pipeline_reports_stage_events(_patch_infra: dict) -> None:
    events: list[tuple[str, str]] = []

    def record(stage: str, status: str, extra: dict) -> None:
        events.append((stage, status))

    run_full_pipeline(_config(search_budget_trials=2), on_event=record)

    # Each trial fires its own ("tune", "trial") event live, in between "tune"/running
    # and "tune"/completed, so the dashboard can plot the search as it happens.
    stage_events = [(s, st) for s, st in events if st != "trial"]
    assert stage_events == [
        ("analyze", "running"),
        ("analyze", "completed"),
        ("migrate", "running"),
        ("migrate", "completed"),
        ("tune", "running"),
        ("tune", "completed"),
        ("benchmark", "running"),
        ("benchmark", "completed"),
        ("report", "running"),
        ("report", "completed"),
    ]
    assert events[0] == ("analyze", "running")
    assert events[-1] == ("report", "completed")

    trial_events = [(s, st) for s, st in events if st == "trial"]
    assert len(trial_events) == 2
    assert all(s == "tune" for s, _ in trial_events)


def test_run_full_pipeline_runs_analysis_when_source_path_given(
    _patch_infra: dict, tmp_path: Path
) -> None:
    (tmp_path / "Dockerfile").write_text("FROM nvidia/cuda:12.4.0\n", encoding="utf-8")

    result = run_full_pipeline(_config(source_path=str(tmp_path), search_budget_trials=2))

    assert result.analysis.is_migration_blocked
    assert any(f.category == "base-image" for f in result.analysis.blockers)


def test_run_full_pipeline_raises_when_no_feasible_trial(
    _patch_infra: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def always_infeasible(ctx, config):
        result = await _fake_deploy_and_benchmark(ctx, config)
        result.accuracy_score = 0.1  # below any reasonable floor
        return result

    monkeypatch.setattr(trial_runner_module, "deploy_and_benchmark", always_infeasible)

    with pytest.raises(RuntimeError, match="no configuration satisfying"):
        run_full_pipeline(_config(search_budget_trials=3))
