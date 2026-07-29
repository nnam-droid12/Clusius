"""Domain types shared across the Clusius engine.

`BenchmarkResult` is the canonical in-process representation of a single benchmark
run; it round-trips to the open schema at `bench/schema/result.schema.json` via
`BenchmarkResult.to_schema_dict()`, so any consumer of a Clusius result.json (a judge,
another team's tooling, the web dashboard) gets a stable, documented contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

Backend = Literal["llamacpp", "vllm"]
Arch = Literal["x86_64", "aarch64"]
KVCachePrecision = Literal["fp16", "int8"]

SCHEMA_VERSION = "1.0.0"


class ThroughputMetrics(BaseModel):
    tokens_per_second: float = Field(ge=0)
    requests_per_second: float = Field(ge=0)


class LatencyPercentiles(BaseModel):
    ttft_p50: float = Field(ge=0)
    inter_token_p50: float | None = Field(default=None, ge=0)
    p50: float = Field(ge=0)
    p95: float = Field(ge=0)
    p99: float = Field(ge=0)


class BenchmarkResult(BaseModel):
    schema_version: str = SCHEMA_VERSION
    run_id: str
    timestamp: datetime
    commit_sha: str
    image_digest: str | None = None

    model: str
    model_hash: str
    backend: Backend
    quant: str
    instance_type: str
    arch: Arch
    price_per_hour: float = Field(ge=0)

    threads: int = Field(ge=1)
    core_pinning: bool | None = None
    batch_size: int | None = Field(default=None, ge=1)
    kv_cache_precision: KVCachePrecision | None = None
    context_length: int | None = Field(default=None, ge=1)
    concurrency: int = Field(ge=1)

    throughput: ThroughputMetrics
    latency_ms: LatencyPercentiles
    cost_per_1m_tokens: float = Field(ge=0)
    accuracy_score: float = Field(ge=0, le=1)

    baseline_ref: str | None = None
    notes: str | None = None

    def to_schema_dict(self) -> dict:
        """Serialize to a plain dict matching `bench/schema/result.schema.json`
        exactly (ISO-8601 timestamp, no null-only defaults omitted implicitly)."""
        return self.model_dump(mode="json", exclude_none=True)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
