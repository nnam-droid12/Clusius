from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from starlette.responses import StreamingResponse

from clusius_api.db.models import Result, Run, Workload
from clusius_api.db.session import get_session
from clusius_api.jobs.queue import get_arq_pool, run_events_channel
from clusius_api.schemas import RunCreate, RunDetailOut, RunOut

router = APIRouter()


@router.post("/runs", response_model=RunOut, status_code=201)
async def create_run(payload: RunCreate, session: AsyncSession = Depends(get_session)) -> Run:
    workload = Workload(
        name=payload.workload_name, model_ref=payload.model_ref, source_path=payload.source_path
    )
    session.add(workload)
    await session.flush()

    run = Run(
        workload_id=workload.id,
        target_mode=payload.target_mode,
        sla_p95_latency_ms=payload.sla_p95_latency_ms,
        sla_accuracy_floor=payload.sla_accuracy_floor,
        cost_ceiling_usd=payload.cost_ceiling_usd,
        search_budget_trials=payload.search_budget_trials,
        target_base_url=payload.target_base_url,
        target_instance_type=payload.target_instance_type,
        target_arch=payload.target_arch,
        target_price_per_hour=payload.target_price_per_hour,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    pool = await get_arq_pool()
    await pool.enqueue_job("run_pipeline", run.id)

    return run


@router.get("/runs", response_model=list[RunOut])
async def list_runs(session: AsyncSession = Depends(get_session)) -> list[Run]:
    result = await session.execute(select(Run).order_by(Run.created_at.desc()))
    return list(result.scalars().all())


@router.get("/runs/{run_id}", response_model=RunDetailOut)
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)) -> Run:
    result = await session.execute(
        select(Run)
        .where(Run.id == run_id)
        .options(selectinload(Run.trials), selectinload(Run.results))
    )
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    return run


@router.get("/runs/{run_id}/events")
async def run_events(
    run_id: str, session: AsyncSession = Depends(get_session)
) -> StreamingResponse:
    run = await session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")

    async def event_stream():
        pool = await get_arq_pool()
        pubsub = pool.pubsub()
        await pubsub.subscribe(run_events_channel(run_id))
        try:
            yield f"data: {json.dumps({'stage': run.stage, 'status': run.status})}\n\n"
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
                if message is not None:
                    data = message["data"]
                    if isinstance(data, bytes):
                        data = data.decode()
                    yield f"data: {data}\n\n"
                else:
                    yield ": keep-alive\n\n"
                await asyncio.sleep(0)
        finally:
            await pubsub.unsubscribe(run_events_channel(run_id))
            await pubsub.aclose()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/runs/{run_id}/result.json")
async def get_run_result(run_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    result = await session.execute(
        select(Result).where(Result.run_id == run_id).order_by(Result.created_at.desc())
    )
    row = result.scalars().first()
    if row is None:
        raise HTTPException(status_code=404, detail="no result recorded for this run yet")
    return row.result_json


@router.get("/results", response_model=list[RunOut])
async def list_results(session: AsyncSession = Depends(get_session)) -> list[Run]:
    result = await session.execute(
        select(Run).where(Run.status == "completed").order_by(Run.updated_at.desc())
    )
    return list(result.scalars().all())
