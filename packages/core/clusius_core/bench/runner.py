"""Ties the load generator, metrics aggregation, and cost model together into a
schema-conformant `BenchmarkResult`, and writes it (plus raw per-request CSV data) to
disk. This is the module other tooling should import to run a Clusius-shaped
benchmark against any OpenAI-compatible endpoint."""

from __future__ import annotations

import csv
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from clusius_core.bench.cost import cost_per_1m_tokens
from clusius_core.bench.load_generator import LoadTestConfig, run_load_test
from clusius_core.bench.metrics import RequestFailure, RequestMetric, aggregate
from clusius_core.bench.schema_validate import validate_result
from clusius_core.models import Arch, Backend, BenchmarkResult, KVCachePrecision, utcnow


@dataclass
class BenchmarkRunConfig:
    base_url: str
    model: str
    prompts: list[str]
    concurrency: int
    commit_sha: str
    model_hash: str
    backend: Backend
    quant: str
    instance_type: str
    arch: Arch
    price_per_hour: float
    threads: int
    accuracy_score: float
    core_pinning: bool | None = None
    batch_size: int | None = None
    kv_cache_precision: KVCachePrecision | None = None
    context_length: int | None = None
    baseline_ref: str | None = None
    notes: str | None = None
    image_digest: str | None = None
    api_key: str = "not-needed"
    request_timeout_s: float = 120.0


async def run_benchmark(
    config: BenchmarkRunConfig,
) -> tuple[BenchmarkResult, list[RequestMetric], list[RequestFailure]]:
    load_config = LoadTestConfig(
        base_url=config.base_url,
        model=config.model,
        prompts=config.prompts,
        concurrency=config.concurrency,
        api_key=config.api_key,
        request_timeout_s=config.request_timeout_s,
    )
    metrics, failures, wall_clock_s = await run_load_test(load_config)
    if not metrics:
        raise RuntimeError(
            f"benchmark produced zero successful requests out of {len(config.prompts)} "
            f"({len(failures)} failures) — refusing to fabricate a result"
        )

    throughput, latency = aggregate(metrics, wall_clock_s)
    cost = cost_per_1m_tokens(config.price_per_hour, throughput.tokens_per_second)

    result = BenchmarkResult(
        run_id=uuid.uuid4().hex,
        timestamp=utcnow(),
        commit_sha=config.commit_sha,
        image_digest=config.image_digest,
        model=config.model,
        model_hash=config.model_hash,
        backend=config.backend,
        quant=config.quant,
        instance_type=config.instance_type,
        arch=config.arch,
        price_per_hour=config.price_per_hour,
        threads=config.threads,
        core_pinning=config.core_pinning,
        batch_size=config.batch_size,
        kv_cache_precision=config.kv_cache_precision,
        context_length=config.context_length,
        concurrency=config.concurrency,
        throughput=throughput,
        latency_ms=latency,
        cost_per_1m_tokens=cost,
        accuracy_score=config.accuracy_score,
        baseline_ref=config.baseline_ref,
        notes=config.notes,
    )
    validate_result(result)
    return result, metrics, failures


def write_result(result: BenchmarkResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result.run_id}.result.json"
    path.write_text(json.dumps(result.to_schema_dict(), indent=2), encoding="utf-8")
    return path


def write_raw_metrics_csv(metrics: list[RequestMetric], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["ttft_s", "total_latency_s", "completion_tokens", "inter_token_latencies_s"]
        )
        for m in metrics:
            writer.writerow(
                [
                    m.ttft_s,
                    m.total_latency_s,
                    m.completion_tokens,
                    json.dumps(m.inter_token_latencies_s),
                ]
            )
    return out_path
