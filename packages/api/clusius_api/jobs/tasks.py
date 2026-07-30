"""The `run_pipeline` arq task: drives a Run through whichever pipeline stages it has
enough configuration to actually execute for real.

Two paths:
- **Full pipeline** (target_mode="target" and both SSH targets are configured on the
  API's own settings, not per-request): drives `clusius_core.pipeline.run_full_pipeline`
  for real over SSH — analyze, migrate (build + prepare the model on both targets),
  tune (a live NSGA-II search), benchmark (the winner replayed on the x86 baseline),
  and report generation.
- **Fallback** (no SSH targets configured): Analyze always runs (it's infra-free —
  just static inspection of the workload's source). Benchmark only runs if the run
  was given a live `target_base_url`. Clusius never fabricates a benchmark result for
  a target it wasn't pointed at.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from clusius_core.analyze.scanner import scan_workload
from clusius_core.bench.runner import BenchmarkRunConfig, run_benchmark
from clusius_core.migrate.ssh_runner import TargetHost
from clusius_core.pipeline import PipelineConfig, run_full_pipeline

from clusius_api.db.models import Artifact, Result, Run, Trial, Workload
from clusius_api.db.session import SessionLocal
from clusius_api.jobs.queue import publish_event
from clusius_api.settings import ApiSettings

DEFAULT_BENCH_PROMPTS = [
    "What is KleidiAI and how does it accelerate inference on Arm?",
    "Summarize the difference between GGUF quantization and INT4 weight-only quantization.",
    "Why would a team pick vLLM over llama.cpp for a high-concurrency deployment?",
]


def _current_commit_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


async def _set_stage(session, redis, run: Run, stage: str, status: str, **extra: Any) -> None:
    run.stage = stage
    run.status = status
    session.add(run)
    await session.commit()
    await publish_event(redis, run.id, {"stage": stage, "status": status, **extra})


def _make_on_event(
    loop: asyncio.AbstractEventLoop, session, redis, run: Run
) -> Callable[[str, str, dict], None]:
    """`run_full_pipeline` runs synchronously inside `asyncio.to_thread`, so its
    `on_event` callback fires from a worker thread — bridge each event back onto the
    main event loop (where `session`/`redis` actually live) and block the worker
    thread until it's persisted, so stage order is preserved."""

    def on_event(stage: str, status: str, extra: dict) -> None:
        future = asyncio.run_coroutine_threadsafe(
            _set_stage(session, redis, run, stage, status, **extra), loop
        )
        future.result()

    return on_event


async def _run_full_ssh_pipeline(
    session, redis, run: Run, workload: Workload, settings: ApiSettings
) -> None:
    arm_target = TargetHost(
        host=settings.target_arm_host,
        user=settings.target_arm_user,
        ssh_key_path=settings.target_arm_ssh_key_path,
        price_per_hour=settings.target_arm_price_per_hour,
    )
    x86_target = TargetHost(
        host=settings.target_x86_host,
        user=settings.target_x86_user,
        ssh_key_path=settings.target_x86_ssh_key_path,
        price_per_hour=settings.target_x86_price_per_hour,
    )
    pipeline_config = PipelineConfig(
        workload_name=workload.name,
        hf_model_id=workload.model_ref or settings.default_hf_model_id,
        source_path=workload.source_path,
        arm_target=arm_target,
        x86_target=x86_target,
        arm_instance_type=settings.target_arm_instance_type,
        x86_instance_type=settings.target_x86_instance_type,
        sla_p95_latency_ms=run.sla_p95_latency_ms,
        sla_accuracy_floor=run.sla_accuracy_floor,
        search_budget_trials=run.search_budget_trials,
        commit_sha=_current_commit_sha(),
        prompts=DEFAULT_BENCH_PROMPTS,
    )

    loop = asyncio.get_running_loop()
    on_event = _make_on_event(loop, session, redis, run)

    result = await asyncio.to_thread(run_full_pipeline, pipeline_config, on_event)

    session.add(
        Result(
            run_id=run.id,
            kind="baseline_x86",
            result_json=result.baseline_result.to_schema_dict(),
        )
    )
    session.add(
        Result(run_id=run.id, kind="arm_winner", result_json=result.winner_result.to_schema_dict())
    )
    session.add(Artifact(run_id=run.id, kind="report_markdown", content=result.report_markdown))
    if result.analysis.findings:
        session.add(
            Artifact(
                run_id=run.id,
                kind="analysis_report",
                content=json.dumps([vars(f) for f in result.analysis.findings]),
            )
        )
    for t in result.trials:
        session.add(
            Trial(
                run_id=run.id,
                trial_number=t.trial_number,
                backend=t.backend,
                quant=t.quant,
                threads=t.threads,
                core_pinning=t.core_pinning,
                batch_size=t.batch_size,
                kv_cache_precision=t.kv_cache_precision,
                context_length=t.context_length,
                tokens_per_second=t.tokens_per_second,
                p95_latency_ms=t.p95_latency_ms,
                cost_per_1m_tokens=t.cost_per_1m_tokens,
                accuracy_score=t.accuracy_score,
                feasible=t.feasible,
            )
        )
    run.selected_backend = result.winner_config.backend
    session.add(run)
    await session.commit()


async def _run_analyze_and_optional_benchmark(session, redis, run: Run, workload: Workload) -> None:
    await _set_stage(session, redis, run, "analyze", "running")
    blocker_count = 0
    if workload.source_path and Path(workload.source_path).is_dir():
        report = scan_workload(Path(workload.source_path))
        blocker_count = len(report.blockers)
        session.add(
            Artifact(
                run_id=run.id,
                kind="analysis_report",
                content=json.dumps([vars(f) for f in report.findings]),
            )
        )
        await session.commit()
    await _set_stage(session, redis, run, "analyze", "completed", blocker_count=blocker_count)

    if run.target_base_url:
        await _set_stage(session, redis, run, "benchmark", "running")
        bench_config = BenchmarkRunConfig(
            base_url=run.target_base_url,
            model=workload.model_ref,
            prompts=DEFAULT_BENCH_PROMPTS,
            concurrency=2,
            commit_sha=_current_commit_sha(),
            model_hash="unknown",
            backend="llamacpp",
            quant="unknown",
            instance_type=run.target_instance_type or "unknown",
            arch=run.target_arch or "x86_64",
            price_per_hour=run.target_price_per_hour or 0.0,
            threads=1,
            accuracy_score=1.0,
        )
        result, _metrics, failures = await run_benchmark(bench_config)
        session.add(Result(run_id=run.id, kind="baseline_x86", result_json=result.to_schema_dict()))
        await session.commit()
        await _set_stage(
            session,
            redis,
            run,
            "benchmark",
            "completed",
            tokens_per_second=result.throughput.tokens_per_second,
            failures=len(failures),
        )


async def run_pipeline(ctx: dict, run_id: str, settings: ApiSettings | None = None) -> None:
    """`settings` is normally left unset — arq always calls this as `run_pipeline(ctx,
    run_id)`, and it defaults to reading the real environment/`.env`. The parameter
    exists so tests can inject an isolated `ApiSettings(_env_file=None)` instead of
    picking up whatever SSH targets happen to be configured on the machine running
    the test suite."""
    redis = ctx["redis"]
    settings = settings or ApiSettings()

    async with SessionLocal() as session:
        run = await session.get(Run, run_id)
        if run is None:
            return
        workload = await session.get(Workload, run.workload_id)

        try:
            if run.target_mode == "target" and settings.ssh_targets_configured:
                await _run_full_ssh_pipeline(session, redis, run, workload, settings)
            else:
                await _run_analyze_and_optional_benchmark(session, redis, run, workload)

            await _set_stage(session, redis, run, "done", "completed")
        except Exception as exc:  # noqa: BLE001 - surface the failure on the run, don't crash the worker
            run.status = "failed"
            run.error_message = str(exc)
            session.add(run)
            await session.commit()
            await publish_event(
                redis, run.id, {"stage": run.stage, "status": "failed", "error": str(exc)}
            )
