"""Replays a real, already-completed Clusius run through the live dashboard —
same DB writes, same Redis pub/sub events, same SSE stream the real arq worker
produces when it drives a live SSH pipeline — using the exact evidence already
committed to `bench/results/`. This is the zero-cost, zero-cloud-credential way to
see the full run experience (stage timeline, trials landing on the Pareto chart one
by one, the generated report) without needing the real C4A + x86 target pair running.

Nothing here is simulated data: every trial, every metric, and the report text are
byte-for-byte the same real, measured numbers documented in the README's "Proof"
section — this script only replays *when* they land, spaced out like a live run
instead of a nonsensically instant flatten of the timeline.

Run via `make demo-replay` (after `make dev` is up), or directly:
    uv run --package clusius-api python -m clusius_api.scripts.demo_replay
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from clusius_api.db.models import Artifact, Result, Run, Trial, Workload
from clusius_api.db.session import SessionLocal
from clusius_api.jobs.queue import ArqRedis, get_arq_pool, publish_event
from clusius_api.settings import ApiSettings

_REPO_ROOT = Path(__file__).resolve().parents[4]
_BENCH_RESULTS = _REPO_ROOT / "bench" / "results"

STAGE_DELAY_S = 1.5
TRIAL_DELAY_S = 1.2


def _latest_evidence() -> tuple[dict[str, Any], str]:
    """Picks the most recent committed run's evidence by filename — evidence files are
    named `<ISO-date>-<workload-slug>.run-detail.json`, so a lexicographic sort is a
    chronological sort. Never hardcodes a specific run, so this keeps working as new
    real runs get committed."""
    candidates = sorted(_BENCH_RESULTS.glob("*.run-detail.json"))
    if not candidates:
        raise SystemExit(
            f"No committed run evidence found in {_BENCH_RESULTS} — nothing to replay. "
            "See the README's 'Proof: A Real, Live, End-to-End Run' section."
        )
    run_detail_path = candidates[-1]
    report_path = run_detail_path.with_name(
        run_detail_path.name.replace(".run-detail.json", ".MIGRATION_REPORT.md")
    )
    run_detail = json.loads(run_detail_path.read_text(encoding="utf-8"))
    report_markdown = (
        report_path.read_text(encoding="utf-8")
        if report_path.exists()
        else "_(no committed report markdown alongside this run's evidence)_"
    )
    return run_detail, report_markdown


async def _set_stage(
    session, pool: ArqRedis, run: Run, stage: str, status: str, **extra: Any
) -> None:
    run.stage = stage
    run.status = status
    session.add(run)
    await session.commit()
    await publish_event(pool, run.id, {"stage": stage, "status": status, **extra})
    await asyncio.sleep(STAGE_DELAY_S)


async def _replay() -> None:
    run_detail, report_markdown = _latest_evidence()
    settings = ApiSettings()
    pool = await get_arq_pool(settings)

    async with SessionLocal() as session:
        workload = Workload(
            name=f"[replay] {run_detail.get('workload_id', 'real-run')}",
            model_ref="Qwen/Qwen2.5-0.5B-Instruct",
            description=(
                "Zero-cost local replay of a real, committed Clusius run — every number "
                "is real, only the timing is simulated. See bench/results/ and the "
                "README's 'Proof' section for the source evidence."
            ),
        )
        session.add(workload)
        await session.flush()

        run = Run(
            workload_id=workload.id,
            status="queued",
            target_mode=run_detail["target_mode"],
            sla_p95_latency_ms=run_detail["sla_p95_latency_ms"],
            sla_accuracy_floor=run_detail["sla_accuracy_floor"],
            search_budget_trials=run_detail["search_budget_trials"],
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

        print(f"Replaying real run evidence as run {run.id}")
        print(f"Dashboard: http://localhost:3000/runs/{run.id}")
        print("(this replays real, committed measurements - it does not drive any live hardware)\n")

        await _set_stage(session, pool, run, "analyze", "running")
        await _set_stage(session, pool, run, "analyze", "completed", blocker_count=0)

        await _set_stage(session, pool, run, "migrate", "running")
        await _set_stage(session, pool, run, "migrate", "completed")

        await _set_stage(session, pool, run, "tune", "running")
        for trial in run_detail["trials"]:
            session.add(
                Trial(
                    run_id=run.id,
                    trial_number=trial["trial_number"],
                    backend=trial["backend"],
                    quant=trial["quant"],
                    threads=trial["threads"],
                    core_pinning=trial["core_pinning"],
                    batch_size=trial["batch_size"],
                    kv_cache_precision=trial["kv_cache_precision"],
                    context_length=trial["context_length"],
                    tokens_per_second=trial["tokens_per_second"],
                    p95_latency_ms=trial["p95_latency_ms"],
                    cost_per_1m_tokens=trial["cost_per_1m_tokens"],
                    accuracy_score=trial["accuracy_score"],
                    feasible=trial["feasible"],
                )
            )
            await session.commit()
            await publish_event(
                pool,
                run.id,
                {
                    "stage": "tune",
                    "status": "trial",
                    "trial_number": trial["trial_number"],
                    "backend": trial["backend"],
                    "quant": trial["quant"],
                    "tokens_per_second": trial["tokens_per_second"],
                    "feasible": trial["feasible"],
                },
            )
            print(
                f"  trial {trial['trial_number']}: {trial['backend']} {trial['quant']} -> "
                f"{trial['tokens_per_second']:.1f} tok/s "
                f"({'feasible' if trial['feasible'] else 'infeasible'})"
            )
            await asyncio.sleep(TRIAL_DELAY_S)
        await _set_stage(
            session, pool, run, "tune", "completed", trial_count=len(run_detail["trials"])
        )

        await _set_stage(session, pool, run, "benchmark", "running")
        winner_backend = None
        for result in run_detail["results"]:
            session.add(
                Result(run_id=run.id, kind=result["kind"], result_json=result["result_json"])
            )
            if result["kind"] == "arm_winner":
                winner_backend = result["result_json"]["backend"]
        await session.commit()
        await _set_stage(session, pool, run, "benchmark", "completed")

        await _set_stage(session, pool, run, "report", "running")
        session.add(Artifact(run_id=run.id, kind="report_markdown", content=report_markdown))
        run.selected_backend = winner_backend
        session.add(run)
        await session.commit()
        await _set_stage(session, pool, run, "report", "completed")

        run.status = "completed"
        run.stage = "done"
        session.add(run)
        await session.commit()
        await publish_event(pool, run.id, {"stage": "done", "status": "completed"})

        print(f"\nDone. View the full replayed run at http://localhost:3000/runs/{run.id}")


def main() -> None:
    asyncio.run(_replay())


if __name__ == "__main__":
    main()
