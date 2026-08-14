"""arq worker entry point: `arq clusius_api.jobs.worker.WorkerSettings`.

arq injects the connection pool into every job's `ctx` as `ctx["redis"]` by default,
which is what `jobs/tasks.py` uses to publish SSE events — no extra startup wiring
needed.
"""

from __future__ import annotations

from datetime import timedelta

from arq.connections import RedisSettings
from arq.typing import WorkerSettingsBase

from clusius_api.jobs.tasks import run_pipeline
from clusius_api.settings import ApiSettings


def _redis_settings() -> RedisSettings:
    # arq's own default conn_timeout is 1 second - too tight for a TLS handshake to a
    # remote managed Redis from Cloud Run, and it was silently failing worker startup
    # entirely (confirmed live: create_pool() timed out on the first attempt every
    # time against Upstash, and the worker's own internal pool creation - unlike the
    # public arq.create_pool() helper - doesn't get a second try). Both bumped well
    # past what a real handshake over the public internet needs.
    settings = RedisSettings.from_dsn(ApiSettings().redis_url)
    settings.conn_timeout = 10
    settings.conn_retries = 10
    return settings


class WorkerSettings(WorkerSettingsBase):
    functions = [run_pipeline]
    redis_settings = _redis_settings()
    # The full SSH pipeline drives a single shared C4A + x86 VM pair — two runs
    # executing concurrently would race on the same container names and ports.
    max_jobs = 1
    # arq's default job_timeout is 300s. A real full pipeline (native docker builds,
    # a multi-GB model download + conversion + quantization, then many tuning trials
    # each doing a server restart + benchmark) can genuinely run for an hour or more —
    # the default would silently kill it partway through.
    job_timeout = timedelta(hours=3)
