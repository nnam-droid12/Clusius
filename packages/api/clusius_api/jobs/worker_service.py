"""Runs the arq worker alongside a minimal health endpoint in a single process, so it
can deploy as an ordinary Cloud Run service (which requires something listening on
$PORT) rather than needing the separate "worker pool" product. Entry point:
`python -m clusius_api.jobs.worker_service`.
"""

from __future__ import annotations

import asyncio
import os

import uvicorn
from arq.worker import create_worker
from fastapi import FastAPI

from clusius_api.jobs.worker import WorkerSettings

app = FastAPI(title="clusius-worker")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def main() -> None:
    worker = create_worker(WorkerSettings)
    worker_task = asyncio.create_task(worker.async_run())

    port = int(os.environ.get("PORT", "8080"))
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)

    try:
        await server.serve()
    finally:
        worker_task.cancel()
        await worker.close()


if __name__ == "__main__":
    asyncio.run(main())
