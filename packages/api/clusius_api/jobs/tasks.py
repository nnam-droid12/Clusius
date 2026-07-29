"""The `run_pipeline` arq task: drives a Run through whichever pipeline stages it has
enough configuration to actually execute for real. Analyze always runs (it's
infra-free — just static inspection of the workload's source). Benchmark only runs if
the run was given a live `target_base_url`; Clusius never fabricates a benchmark
result for a target it wasn't pointed at.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from clusius_core.analyze.scanner import scan_workload
from clusius_core.bench.runner import BenchmarkRunConfig, run_benchmark

from clusius_api.db.models import Artifact, Result, Run, Workload
from clusius_api.db.session import SessionLocal
from clusius_api.jobs.queue import publish_event

DEFAULT_BENCH_PROMPTS = [
    "What is KleidiAI and how does it accelerate inference on Arm?",
    "Summarize the difference between GGUF quantization and INT4 weight-only quantization.",
    "Why would a team pick vLLM over llama.cpp for a high-concurrency deployment?",
]


async def _set_stage(session, redis, run: Run, stage: str, status: str, **extra: Any) -> None:
    run.stage = stage
    run.status = status
    session.add(run)
    await session.commit()
    await publish_event(redis, run.id, {"stage": stage, "status": status, **extra})


async def run_pipeline(ctx: dict, run_id: str) -> None:
    redis = ctx["redis"]

    async with SessionLocal() as session:
        run = await session.get(Run, run_id)
        if run is None:
            return
        workload = await session.get(Workload, run.workload_id)

        try:
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
            await _set_stage(
                session, redis, run, "analyze", "completed", blocker_count=blocker_count
            )

            if run.target_base_url:
                await _set_stage(session, redis, run, "benchmark", "running")
                bench_config = BenchmarkRunConfig(
                    base_url=run.target_base_url,
                    model=workload.model_ref,
                    prompts=DEFAULT_BENCH_PROMPTS,
                    concurrency=2,
                    commit_sha="unknown",
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
                session.add(
                    Result(run_id=run.id, kind="baseline_x86", result_json=result.to_schema_dict())
                )
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

            await _set_stage(session, redis, run, "done", "completed")
        except Exception as exc:  # noqa: BLE001 - surface the failure on the run, don't crash the worker
            run.status = "failed"
            run.error_message = str(exc)
            session.add(run)
            await session.commit()
            await publish_event(
                redis, run.id, {"stage": run.stage, "status": "failed", "error": str(exc)}
            )
