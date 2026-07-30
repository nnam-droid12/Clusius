from __future__ import annotations

from datetime import UTC, datetime

import pytest
from clusius_api.db.models import Artifact, Result, Run, Trial, Workload
from clusius_api.jobs import tasks as tasks_module
from clusius_api.jobs.tasks import run_pipeline
from clusius_api.settings import ApiSettings
from clusius_core.analyze.scanner import AnalysisReport, Finding
from clusius_core.models import BenchmarkResult, LatencyPercentiles, ThroughputMetrics
from clusius_core.pipeline import PipelineResult, TrialSummary
from clusius_core.tune.search_space import TrialConfig
from sqlalchemy import select

from tests.conftest import TestSessionLocal


class FakeRedis:
    def __init__(self) -> None:
        self.published: list[tuple[str, str]] = []

    async def publish(self, channel: str, message: str) -> None:
        self.published.append((channel, message))


def _ssh_configured_settings() -> ApiSettings:
    return ApiSettings(
        _env_file=None,
        target_arm_host="10.0.0.1",
        target_arm_user="clusius",
        target_x86_host="10.0.0.2",
        target_x86_user="clusius",
    )


def _no_ssh_settings() -> ApiSettings:
    return ApiSettings(_env_file=None)


def _bench_result(**overrides) -> BenchmarkResult:
    defaults = dict(
        run_id="r",
        timestamp=datetime.now(UTC),
        commit_sha="abc123",
        model="Qwen/Qwen2.5-0.5B-Instruct",
        model_hash="Qwen/Qwen2.5-0.5B-Instruct",
        backend="llamacpp",
        quant="Q4_K_M",
        instance_type="c4a-standard-2",
        arch="aarch64",
        price_per_hour=0.1,
        threads=2,
        concurrency=2,
        throughput=ThroughputMetrics(tokens_per_second=40.0, requests_per_second=1.0),
        latency_ms=LatencyPercentiles(ttft_p50=10.0, p50=200.0, p95=400.0, p99=500.0),
        cost_per_1m_tokens=1.5,
        accuracy_score=0.95,
    )
    defaults.update(overrides)
    return BenchmarkResult(**defaults)


def _fake_pipeline_result() -> PipelineResult:
    winner_config = TrialConfig(
        backend="llamacpp",
        quant="Q4_K_M",
        threads=2,
        core_pinning=True,
        batch_size=1,
        kv_cache_precision="int8",
        context_length=2048,
    )
    return PipelineResult(
        analysis=AnalysisReport(
            findings=[
                Finding(
                    severity="blocker",
                    category="cuda",
                    file="Dockerfile",
                    line=1,
                    message="CUDA base image",
                )
            ]
        ),
        baseline_result=_bench_result(arch="x86_64", instance_type="c4-standard-2"),
        winner_result=_bench_result(),
        winner_config=winner_config,
        backend_justification="Selected llama.cpp: fastest feasible config.",
        report_markdown="# Migration Report\n\nSelected llama.cpp.",
        trials=[
            TrialSummary(
                trial_number=0,
                backend="llamacpp",
                quant="Q4_K_M",
                threads=2,
                core_pinning=True,
                batch_size=1,
                kv_cache_precision="int8",
                context_length=2048,
                tokens_per_second=40.0,
                p95_latency_ms=400.0,
                cost_per_1m_tokens=1.5,
                accuracy_score=0.95,
                feasible=True,
            )
        ],
    )


async def _create_run(target_mode: str = "target") -> str:
    async with TestSessionLocal() as session:
        workload = Workload(name="showcase-agent", model_ref="Qwen/Qwen2.5-0.5B-Instruct")
        session.add(workload)
        await session.flush()
        run = Run(
            workload_id=workload.id,
            target_mode=target_mode,
            sla_p95_latency_ms=1000.0,
            sla_accuracy_floor=0.9,
            search_budget_trials=4,
        )
        session.add(run)
        await session.commit()
        return run.id


@pytest.fixture(autouse=True)
def _isolate_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tasks_module, "SessionLocal", TestSessionLocal)


async def test_run_pipeline_uses_full_ssh_path_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_full_pipeline(config, on_event):
        on_event("analyze", "running", {})
        on_event("analyze", "completed", {"blocker_count": 1})
        on_event("report", "completed", {})
        return _fake_pipeline_result()

    monkeypatch.setattr(tasks_module, "run_full_pipeline", fake_run_full_pipeline)

    run_id = await _create_run(target_mode="target")
    redis = FakeRedis()

    await run_pipeline({"redis": redis}, run_id, settings=_ssh_configured_settings())

    async with TestSessionLocal() as session:
        run = await session.get(Run, run_id)
        assert run.status == "completed"
        assert run.stage == "done"
        assert run.selected_backend == "llamacpp"

        trials_result = await session.execute(select(Trial).where(Trial.run_id == run_id))
        trials = trials_result.scalars().all()
        assert len(trials) == 1
        assert trials[0].tokens_per_second == 40.0

        results = (
            (await session.execute(select(Result).where(Result.run_id == run_id))).scalars().all()
        )
        kinds = {r.kind for r in results}
        assert kinds == {"baseline_x86", "arm_winner"}

        artifacts_result = await session.execute(select(Artifact).where(Artifact.run_id == run_id))
        artifacts = artifacts_result.scalars().all()
        artifact_kinds = {a.kind for a in artifacts}
        assert "report_markdown" in artifact_kinds
        assert "analysis_report" in artifact_kinds

    assert any("analyze" in msg for _, msg in redis.published)


async def test_run_pipeline_falls_back_to_analyze_only_when_ssh_not_configured() -> None:
    run_id = await _create_run(target_mode="target")
    redis = FakeRedis()

    await run_pipeline({"redis": redis}, run_id, settings=_no_ssh_settings())

    async with TestSessionLocal() as session:
        run = await session.get(Run, run_id)
        assert run.status == "completed"
        assert run.stage == "done"
        assert run.selected_backend is None


async def test_run_pipeline_marks_run_failed_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_pipeline(config, on_event):
        on_event("analyze", "running", {})
        raise RuntimeError("SSH connection refused")

    monkeypatch.setattr(tasks_module, "run_full_pipeline", failing_pipeline)

    run_id = await _create_run(target_mode="target")
    redis = FakeRedis()

    await run_pipeline({"redis": redis}, run_id, settings=_ssh_configured_settings())

    async with TestSessionLocal() as session:
        run = await session.get(Run, run_id)
        assert run.status == "failed"
        assert "SSH connection refused" in run.error_message
