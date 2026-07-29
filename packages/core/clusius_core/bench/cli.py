"""Command-line entry point for running a standalone Clusius benchmark against any
OpenAI-compatible endpoint. Useful on its own (outside the full agentic pipeline) as a
reusable Arm-migration benchmarking tool."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
from pathlib import Path

from clusius_core.bench.runner import (
    BenchmarkRunConfig,
    run_benchmark,
    write_raw_metrics_csv,
    write_result,
)


def _current_commit_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _load_prompts(path: Path) -> list[str]:
    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines()]
    return [line for line in lines if line]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="clusius-bench")
    parser.add_argument(
        "--base-url",
        required=True,
        help="OpenAI-compatible base URL, e.g. http://localhost:8090/v1",
    )
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--prompts", required=True, type=Path, help="Path to a newline-delimited prompt file"
    )
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--backend", required=True, choices=["llamacpp", "vllm"])
    parser.add_argument("--quant", required=True)
    parser.add_argument("--instance-type", required=True)
    parser.add_argument("--arch", required=True, choices=["x86_64", "aarch64"])
    parser.add_argument("--price-per-hour", required=True, type=float)
    parser.add_argument("--threads", required=True, type=int)
    parser.add_argument("--model-hash", required=True)
    parser.add_argument("--accuracy-score", required=True, type=float)
    parser.add_argument("--out-dir", type=Path, default=Path("bench/results"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = BenchmarkRunConfig(
        base_url=args.base_url,
        model=args.model,
        prompts=_load_prompts(args.prompts),
        concurrency=args.concurrency,
        commit_sha=_current_commit_sha(),
        model_hash=args.model_hash,
        backend=args.backend,
        quant=args.quant,
        instance_type=args.instance_type,
        arch=args.arch,
        price_per_hour=args.price_per_hour,
        threads=args.threads,
        accuracy_score=args.accuracy_score,
    )
    result, metrics, failures = asyncio.run(run_benchmark(config))

    result_path = write_result(result, args.out_dir)
    csv_path = write_raw_metrics_csv(metrics, args.out_dir / f"{result.run_id}.raw.csv")

    print(f"wrote {result_path}")
    print(f"wrote {csv_path}")
    print(f"throughput: {result.throughput.tokens_per_second:.2f} tok/s")
    print(f"p95 latency: {result.latency_ms.p95:.1f} ms")
    print(f"cost per 1M tokens: ${result.cost_per_1m_tokens:.4f}")
    if failures:
        print(f"warning: {len(failures)} requests failed")


if __name__ == "__main__":
    main()
