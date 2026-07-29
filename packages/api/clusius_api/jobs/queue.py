"""arq/Redis connection helpers shared by the API (to enqueue jobs, publish SSE
events) and the worker (to consume jobs)."""

from __future__ import annotations

import json

from arq import ArqRedis, create_pool
from arq.connections import RedisSettings

from clusius_api.settings import ApiSettings

_pool: ArqRedis | None = None


def redis_settings_from_url(redis_url: str) -> RedisSettings:
    return RedisSettings.from_dsn(redis_url)


async def get_arq_pool(settings: ApiSettings | None = None) -> ArqRedis:
    global _pool
    if _pool is None:
        settings = settings or ApiSettings()
        _pool = await create_pool(redis_settings_from_url(settings.redis_url))
    return _pool


def run_events_channel(run_id: str) -> str:
    return f"clusius:run:{run_id}:events"


async def publish_event(pool: ArqRedis, run_id: str, event: dict) -> None:
    await pool.publish(run_events_channel(run_id), json.dumps(event))
