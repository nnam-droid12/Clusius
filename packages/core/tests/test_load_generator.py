"""Validates the load generator against a real (if minimal) streaming ASGI server —
not a hand-mocked HTTP client — so the SSE parsing, TTFT/inter-token timing, and
concurrency control are proven against actual request/response I/O."""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest
from clusius_core.bench.load_generator import LoadTestConfig, run_load_test


async def _fake_openai_app(scope, receive, send):
    assert scope["type"] == "http"
    await receive()
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/event-stream")],
        }
    )
    for token in ["Hel", "lo", " wor", "ld", "!"]:
        chunk = {"choices": [{"delta": {"content": token}}]}
        body = f"data: {json.dumps(chunk)}\n\n".encode()
        await send({"type": "http.response.body", "body": body, "more_body": True})
        await asyncio.sleep(0.01)
    await send({"type": "http.response.body", "body": b"data: [DONE]\n\n", "more_body": False})


@pytest.fixture
def patched_client(monkeypatch: pytest.MonkeyPatch) -> None:
    real_async_client = httpx.AsyncClient

    def fake_async_client(*args, **kwargs):
        kwargs.pop("base_url", None)
        return real_async_client(
            transport=httpx.ASGITransport(app=_fake_openai_app), base_url="http://test", **kwargs
        )

    monkeypatch.setattr(httpx, "AsyncClient", fake_async_client)


async def test_run_load_test_measures_real_streaming_timing(patched_client: None) -> None:
    config = LoadTestConfig(
        base_url="http://test",
        model="fake-model",
        prompts=["hello", "world", "third prompt"],
        concurrency=2,
    )

    metrics, failures, wall_clock_s = await run_load_test(config)

    assert failures == []
    assert len(metrics) == 3
    assert wall_clock_s > 0
    for metric in metrics:
        assert metric.completion_tokens == 5
        assert metric.ttft_s > 0
        assert metric.total_latency_s >= metric.ttft_s
        assert len(metric.inter_token_latencies_s) == 4
