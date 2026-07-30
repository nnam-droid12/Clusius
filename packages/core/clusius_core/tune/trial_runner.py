"""Wires a `TrialConfig` from the search space to a live deployment on the SSH
target and a real benchmark run against it — this is the `evaluate` callback
`clusius_core.tune.optimizer.run_search` needs. Each trial: start the server with
the trial's config, wait for it to become healthy, run the benchmark harness against
it, then tear the server down — regardless of outcome, so a failed trial never leaves
a stray container occupying the target's ports for the next one.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass

from clusius_core.bench.runner import BenchmarkRunConfig, run_benchmark
from clusius_core.migrate import deploy
from clusius_core.migrate.ssh_runner import TargetRunner
from clusius_core.models import Arch, Backend, BenchmarkResult
from clusius_core.tune.search_space import TrialConfig


@dataclass
class RemoteTrialContext:
    runner: TargetRunner
    target_host: str
    instance_type: str
    arch: Arch
    price_per_hour: float
    commit_sha: str
    model_hash: str
    llamacpp_image_tag: str
    vllm_image_tag: str
    llamacpp_gguf_paths: dict[str, str]  # quant -> remote path to the .gguf file
    vllm_model_ref: str  # HF ref (or a pre-quantized model dir) vLLM serves directly
    prompts: list[str]
    concurrency: int
    accuracy_scores: dict[tuple[Backend, str], float]  # (backend, quant) -> score


def _accuracy_for(ctx: RemoteTrialContext, config: TrialConfig) -> float:
    key = (config.backend, config.quant)
    if key not in ctx.accuracy_scores:
        raise KeyError(
            f"no accuracy score recorded for backend={config.backend!r} quant={config.quant!r} "
            "— run the accuracy guard for this (backend, quant) pair before tuning"
        )
    return ctx.accuracy_scores[key]


async def deploy_and_benchmark(ctx: RemoteTrialContext, config: TrialConfig) -> BenchmarkResult:
    port = deploy.server_port(config.backend)
    if config.backend == "llamacpp":
        model_name = ctx.llamacpp_gguf_paths[config.quant]
        deploy.start_llamacpp_server(
            ctx.runner, ctx.llamacpp_image_tag, model_name, config, port=port
        )
    else:
        model_name = ctx.vllm_model_ref
        deploy.start_vllm_server(ctx.runner, ctx.vllm_image_tag, model_name, config, port=port)

    server_root = f"http://{ctx.target_host}:{port}"
    api_base = f"{server_root}/v1"

    try:
        await deploy.wait_for_health(server_root)

        bench_config = BenchmarkRunConfig(
            base_url=api_base,
            model=model_name,
            prompts=ctx.prompts,
            concurrency=ctx.concurrency,
            commit_sha=ctx.commit_sha,
            model_hash=ctx.model_hash,
            backend=config.backend,
            quant=config.quant,
            instance_type=ctx.instance_type,
            arch=ctx.arch,
            price_per_hour=ctx.price_per_hour,
            threads=config.threads,
            core_pinning=config.core_pinning,
            batch_size=config.batch_size,
            kv_cache_precision=config.kv_cache_precision,
            context_length=config.context_length,
            accuracy_score=_accuracy_for(ctx, config),
        )
        result, _metrics, failures = await run_benchmark(bench_config)
        if failures:
            raise RuntimeError(
                f"{len(failures)}/{len(ctx.prompts)} requests failed during trial "
                f"(backend={config.backend}, quant={config.quant})"
            )
        return result
    finally:
        deploy.stop_server(ctx.runner)


def make_trial_evaluator(ctx: RemoteTrialContext) -> Callable[[TrialConfig], BenchmarkResult]:
    def evaluate(config: TrialConfig) -> BenchmarkResult:
        return asyncio.run(deploy_and_benchmark(ctx, config))

    return evaluate
