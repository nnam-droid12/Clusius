"""arq worker entry point: `arq clusius_api.jobs.worker.WorkerSettings`.

arq injects the connection pool into every job's `ctx` as `ctx["redis"]` by default,
which is what `jobs/tasks.py` uses to publish SSE events — no extra startup wiring
needed.
"""

from __future__ import annotations

from arq.connections import RedisSettings

from clusius_api.jobs.tasks import run_pipeline
from clusius_api.settings import ApiSettings


class WorkerSettings:
    functions = [run_pipeline]
    redis_settings = RedisSettings.from_dsn(ApiSettings().redis_url)
    # The full SSH pipeline drives a single shared C4A + x86 VM pair — two runs
    # executing concurrently would race on the same container names and ports.
    max_jobs = 1
