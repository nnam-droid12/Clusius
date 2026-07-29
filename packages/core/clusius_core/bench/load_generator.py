"""Async load generator: replays a fixed prompt set against an OpenAI-compatible
`/v1/chat/completions` streaming endpoint at a configured concurrency, and records
per-request TTFT, inter-token latency, and total latency.

Deterministic by construction: the same `prompts` list, driven at the same
`concurrency`, produces the same request sequence every run — only the timing varies
with the server under test.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass

import httpx

from clusius_core.bench.metrics import RequestFailure, RequestMetric


@dataclass
class LoadTestConfig:
    base_url: str
    model: str
    prompts: list[str]
    concurrency: int
    api_key: str = "not-needed"
    request_timeout_s: float = 120.0


async def _stream_one(client: httpx.AsyncClient, config: LoadTestConfig, prompt: str) -> RequestMetric:
    start = time.perf_counter()
    first_token_at: float | None = None
    last_token_at = start
    inter_token: list[float] = []
    completion_tokens = 0

    async with client.stream(
        "POST",
        "/chat/completions",
        json={
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
        },
        timeout=config.request_timeout_s,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            payload = line.removeprefix("data:").strip()
            if payload == "[DONE]":
                break
            chunk = json.loads(payload)
            delta = chunk.get("choices", [{}])[0].get("delta", {})
            if not delta.get("content"):
                continue
            now = time.perf_counter()
            if first_token_at is None:
                first_token_at = now
            else:
                inter_token.append(now - last_token_at)
            last_token_at = now
            completion_tokens += 1

    end = time.perf_counter()
    if first_token_at is None:
        # No streamed content tokens observed; treat the whole request as the TTFT.
        first_token_at = end

    return RequestMetric(
        ttft_s=first_token_at - start,
        total_latency_s=end - start,
        completion_tokens=completion_tokens,
        inter_token_latencies_s=inter_token,
    )


async def run_load_test(config: LoadTestConfig) -> tuple[list[RequestMetric], list[RequestFailure], float]:
    """Returns (successful request metrics, failures, wall-clock seconds for the whole
    batch) so throughput can be computed against real elapsed time, not summed
    per-request latency."""
    semaphore = asyncio.Semaphore(config.concurrency)
    metrics: list[RequestMetric] = []
    failures: list[RequestFailure] = []

    async def bound_call(client: httpx.AsyncClient, prompt: str) -> None:
        async with semaphore:
            try:
                metrics.append(await _stream_one(client, config, prompt))
            except Exception as exc:  # noqa: BLE001 - a failed request is a data point, not a crash
                failures.append(RequestFailure(error=str(exc)))

    async with httpx.AsyncClient(
        base_url=config.base_url, headers={"Authorization": f"Bearer {config.api_key}"}
    ) as client:
        start = time.perf_counter()
        await asyncio.gather(*(bound_call(client, prompt) for prompt in config.prompts))
        wall_clock_s = time.perf_counter() - start

    return metrics, failures, wall_clock_s
