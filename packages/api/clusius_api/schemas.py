"""API request/response models. Kept separate from the SQLAlchemy models (db/models.py)
so the wire schema can evolve independently of the storage schema."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict


class RunCreate(BaseModel):
    workload_name: str
    model_ref: str
    source_path: str | None = None
    target_mode: Literal["target", "provisioned"] = "target"
    sla_p95_latency_ms: float
    sla_accuracy_floor: float
    cost_ceiling_usd: float | None = None
    search_budget_trials: int = 20
    # llama.cpp+KleidiAI favors low-concurrency/single-stream; vLLM's continuous
    # batching favors high-concurrency batched throughput — the tuner probes both
    # backends against whichever value is set here, so this is the one knob that
    # actually shapes which backend has a real chance of winning.
    concurrency: int = 2
    # If set, the pipeline job benchmarks this live OpenAI-compatible endpoint as
    # part of the run. Left unset, the run only performs the (infra-free) analyze
    # stage — Clusius never fabricates a benchmark result for an endpoint it wasn't
    # given.
    target_base_url: str | None = None
    target_instance_type: str | None = None
    target_arch: Literal["x86_64", "aarch64"] | None = None
    target_price_per_hour: float | None = None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    workload_id: str
    status: str
    stage: str | None
    target_mode: str
    sla_p95_latency_ms: float
    sla_accuracy_floor: float
    cost_ceiling_usd: float | None
    search_budget_trials: int
    concurrency: int
    selected_backend: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class TrialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    trial_number: int
    backend: str
    quant: str
    threads: int
    core_pinning: bool
    batch_size: int
    kv_cache_precision: str
    context_length: int
    tokens_per_second: float
    p95_latency_ms: float
    cost_per_1m_tokens: float
    accuracy_score: float
    feasible: bool
    created_at: datetime


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    result_json: dict[str, Any]
    created_at: datetime


class ArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    kind: str
    path: str | None
    digest: str | None
    created_at: datetime


class RunDetailOut(RunOut):
    trials: list[TrialOut] = []
    results: list[ResultOut] = []
    artifacts: list[ArtifactOut] = []


class RunSummaryOut(BaseModel):
    """Lighter than RunDetailOut — just enough per run to render a results gallery
    (workload identity + baseline/winner results) without the full trial history."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    target_mode: str
    selected_backend: str | None
    created_at: datetime
    updated_at: datetime
    workload_name: str
    model_ref: str
    results: list[ResultOut] = []
