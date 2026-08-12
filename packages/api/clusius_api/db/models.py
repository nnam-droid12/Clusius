"""SQLAlchemy models for the five persisted entities: Workload, Run, Trial, Result,
Artifact. Owned entirely by clusius-api — the web app never touches the database
directly, only this API's REST/SSE surface.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Workload(Base):
    __tablename__ = "workloads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    model_ref: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    runs: Mapped[list[Run]] = relationship(back_populates="workload")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workload_id: Mapped[str] = mapped_column(ForeignKey("workloads.id"))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    stage: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_mode: Mapped[str] = mapped_column(String(16), default="target")

    sla_p95_latency_ms: Mapped[float] = mapped_column(Float)
    sla_accuracy_floor: Mapped[float] = mapped_column(Float)
    cost_ceiling_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    search_budget_trials: Mapped[int] = mapped_column(Integer, default=20)
    # llama.cpp+KleidiAI favors low-concurrency/single-stream; vLLM's continuous
    # batching favors high-concurrency - every real run so far used the default (2),
    # which is exactly the regime that favors llama.cpp and is why vLLM had never even
    # been sampled by the search, let alone won a trial.
    concurrency: Mapped[int] = mapped_column(Integer, default=2)

    target_base_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    target_instance_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_arch: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_price_per_hour: Mapped[float | None] = mapped_column(Float, nullable=True)

    selected_backend: Mapped[str | None] = mapped_column(String(16), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    workload: Mapped[Workload] = relationship(back_populates="runs")
    trials: Mapped[list[Trial]] = relationship(back_populates="run", order_by="Trial.trial_number")
    results: Mapped[list[Result]] = relationship(back_populates="run")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="run")


class Trial(Base):
    __tablename__ = "trials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    trial_number: Mapped[int] = mapped_column(Integer)

    backend: Mapped[str] = mapped_column(String(16))
    quant: Mapped[str] = mapped_column(String(32))
    threads: Mapped[int] = mapped_column(Integer)
    core_pinning: Mapped[bool] = mapped_column(default=False)
    batch_size: Mapped[int] = mapped_column(Integer)
    kv_cache_precision: Mapped[str] = mapped_column(String(8))
    context_length: Mapped[int] = mapped_column(Integer)

    tokens_per_second: Mapped[float] = mapped_column(Float)
    p95_latency_ms: Mapped[float] = mapped_column(Float)
    cost_per_1m_tokens: Mapped[float] = mapped_column(Float)
    accuracy_score: Mapped[float] = mapped_column(Float)
    feasible: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    run: Mapped[Run] = relationship(back_populates="trials")


class Result(Base):
    __tablename__ = "results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    kind: Mapped[str] = mapped_column(String(32))  # "baseline_x86" | "arm_winner"
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    run: Mapped[Run] = relationship(back_populates="results")


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(ForeignKey("runs.id"))
    kind: Mapped[str] = mapped_column(String(32))  # "report_markdown" | "image_digest" | ...
    path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    digest: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    run: Mapped[Run] = relationship(back_populates="artifacts")
