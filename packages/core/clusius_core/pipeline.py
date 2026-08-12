"""The full five-stage pipeline: analyze -> migrate -> tune -> benchmark -> report,
driving a real C4A + x86 SSH target pair. This is what
`clusius_api.jobs.tasks.run_pipeline` calls once a run has target-mode SSH
configuration for both an Arm and an x86 host.

Deliberately synchronous throughout: Optuna's `Study.optimize` is a blocking call with
no native asyncio integration, and each trial's deploy+benchmark round trip already
opens and fully closes its own event loop (see `tune.trial_runner`) — nesting another
one here would raise "asyncio.run() cannot be called from a running event loop". The
API's arq job runs this whole function inside `asyncio.to_thread(...)` so it doesn't
block the worker's own event loop.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from clusius_core.analyze.scanner import AnalysisReport, scan_workload
from clusius_core.migrate import deploy, model_prep
from clusius_core.migrate.ssh_runner import TargetHost, TargetRunner
from clusius_core.models import Backend, BenchmarkResult
from clusius_core.report.generator import MigrationReportInputs, render_migration_report
from clusius_core.tune.backend_selector import BackendProbeResult, select_backend
from clusius_core.tune.optimizer import TunerConfig, pareto_frontier, run_search
from clusius_core.tune.search_space import SearchSpace, TrialConfig
from clusius_core.tune.trial_runner import RemoteTrialContext, make_trial_evaluator

_REPO_ROOT = Path(__file__).resolve().parents[3]
LLAMACPP_DOCKERFILE = _REPO_ROOT / "infra" / "docker" / "llamacpp-kleidi.Dockerfile"

StageEvent = Callable[[str, str, dict[str, Any]], None]


def _noop_event(stage: str, status: str, extra: dict[str, Any]) -> None:
    return None


@dataclass
class PipelineConfig:
    workload_name: str
    hf_model_id: str
    source_path: str | None
    arm_target: TargetHost
    x86_target: TargetHost
    arm_instance_type: str
    x86_instance_type: str
    sla_p95_latency_ms: float
    sla_accuracy_floor: float
    search_budget_trials: int
    commit_sha: str
    prompts: list[str]
    concurrency: int = 2
    threads_options: list[int] = field(default_factory=lambda: [1, 2])
    quant_types: list[str] = field(default_factory=lambda: ["Q4_K_M", "Q8_0"])
    context_lengths: list[int] = field(default_factory=lambda: [2048])
    # llama-server defaults to 4 parallel slots (no --parallel override in
    # deploy.start_llamacpp_server), and its internal output-buffer sizing requires
    # --batch-size >= slot count — batch_size=1 hits a real, reproducible
    # GGML_ASSERT(n_outputs_max <= cparams.n_outputs_max) crash on startup, confirmed
    # live against the real Arm target. 1 is deliberately excluded here, not just
    # untested.
    batch_sizes: list[int] = field(default_factory=lambda: [2, 4])


@dataclass
class TrialSummary:
    trial_number: int
    backend: Backend
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


@dataclass
class PipelineResult:
    analysis: AnalysisReport
    baseline_result: BenchmarkResult
    winner_result: BenchmarkResult
    winner_config: TrialConfig
    backend_justification: str
    report_markdown: str
    trials: list[TrialSummary]


def _describe_optimizations(config: TrialConfig) -> list[str]:
    items = [f"{config.quant} quantization", f"{config.threads} threads"]
    if config.backend == "llamacpp":
        items.append("KleidiAI CPU kernels linked (Arm build)")
    if config.core_pinning:
        items.append("core pinning enabled")
    items.append(f"KV cache precision: {config.kv_cache_precision}")
    return items


def run_full_pipeline(config: PipelineConfig, on_event: StageEvent = _noop_event) -> PipelineResult:
    # --- Analyze ---
    on_event("analyze", "running", {})
    analysis = AnalysisReport(findings=[])
    if config.source_path and Path(config.source_path).is_dir():
        analysis = scan_workload(Path(config.source_path))
    on_event("analyze", "completed", {"blocker_count": len(analysis.blockers)})

    # --- Migrate: build llama.cpp natively on both targets, prepare the model ---
    on_event("migrate", "running", {})
    arm_runner = TargetRunner(config.arm_target)
    x86_runner = TargetRunner(config.x86_target)

    deploy.ensure_docker_installed(arm_runner)
    deploy.ensure_docker_installed(x86_runner)

    arm_image_tag = "clusius-llamacpp:arm"
    x86_image_tag = "clusius-llamacpp:x86"
    deploy.build_backend_image(
        arm_runner, str(LLAMACPP_DOCKERFILE), arm_image_tag, {"ENABLE_KLEIDIAI": "ON"}
    )
    deploy.build_backend_image(
        x86_runner, str(LLAMACPP_DOCKERFILE), x86_image_tag, {"ENABLE_KLEIDIAI": "OFF"}
    )

    arm_gguf_paths = model_prep.prepare_gguf_models(
        arm_runner, arm_image_tag, config.hf_model_id, config.quant_types
    )
    x86_gguf_paths = model_prep.prepare_gguf_models(
        x86_runner, x86_image_tag, config.hf_model_id, config.quant_types
    )
    on_event("migrate", "completed", {})

    # --- Tune: NSGA-II search on the Arm target ---
    on_event("tune", "running", {})
    # A real accuracy guard belongs here once a task-appropriate eval set is wired in;
    # until then every quant is treated as passing so the SLA/latency constraints are
    # still real and enforced, but accuracy is not yet a live search signal.
    accuracy_scores: dict[tuple[Backend, str], float] = {
        ("llamacpp", q): 1.0 for q in config.quant_types
    }
    arm_price = config.arm_target.price_per_hour or 0.0
    trial_ctx = RemoteTrialContext(
        runner=arm_runner,
        target_host=config.arm_target.host,
        instance_type=config.arm_instance_type,
        arch="aarch64",
        price_per_hour=arm_price,
        commit_sha=config.commit_sha,
        model_hash=config.hf_model_id,
        llamacpp_image_tag=arm_image_tag,
        vllm_image_tag="",
        llamacpp_gguf_paths=arm_gguf_paths,
        vllm_model_ref=config.hf_model_id,
        prompts=config.prompts,
        concurrency=config.concurrency,
        accuracy_scores=accuracy_scores,
    )
    evaluator = make_trial_evaluator(trial_ctx)
    trial_history: list[tuple[TrialConfig, BenchmarkResult]] = []

    def evaluate(trial_config: TrialConfig) -> BenchmarkResult:
        result = evaluator(trial_config)
        trial_history.append((trial_config, result))
        feasible = (
            result.accuracy_score >= config.sla_accuracy_floor
            and result.latency_ms.p95 <= config.sla_p95_latency_ms
        )
        # Streamed the instant each trial finishes (not batched at the end) so a live
        # dashboard can plot the search converging in real time, trial by trial.
        on_event(
            "tune",
            "trial",
            {
                "trial_number": len(trial_history) - 1,
                "backend": trial_config.backend,
                "quant": trial_config.quant,
                "threads": trial_config.threads,
                "core_pinning": trial_config.core_pinning,
                "batch_size": trial_config.batch_size,
                "kv_cache_precision": trial_config.kv_cache_precision,
                "context_length": trial_config.context_length,
                "tokens_per_second": result.throughput.tokens_per_second,
                "p95_latency_ms": result.latency_ms.p95,
                "cost_per_1m_tokens": result.cost_per_1m_tokens,
                "accuracy_score": result.accuracy_score,
                "feasible": feasible,
            },
        )
        return result

    search_space = SearchSpace(
        threads=config.threads_options,
        batch_sizes=config.batch_sizes,
        context_lengths=config.context_lengths,
        backends=["llamacpp"],
        llamacpp_quants=config.quant_types,
    )
    tuner_config = TunerConfig(
        max_trials=config.search_budget_trials,
        accuracy_floor=config.sla_accuracy_floor,
        latency_sla_ms=config.sla_p95_latency_ms,
    )
    study = run_search(search_space, tuner_config, evaluate)
    frontier = pareto_frontier(study)
    if not frontier:
        raise RuntimeError(
            "auto-tune search found no configuration satisfying the accuracy floor and latency SLA"
        )
    best_trial = max(frontier, key=lambda t: t.values[0])
    winner_config, winner_result = trial_history[best_trial.number]
    on_event("tune", "completed", {"trial_count": len(study.trials)})

    # --- Benchmark: the winning config, replayed on the x86 baseline ---
    on_event("benchmark", "running", {})
    x86_price = config.x86_target.price_per_hour or 0.0
    baseline_ctx = RemoteTrialContext(
        runner=x86_runner,
        target_host=config.x86_target.host,
        instance_type=config.x86_instance_type,
        arch="x86_64",
        price_per_hour=x86_price,
        commit_sha=config.commit_sha,
        model_hash=config.hf_model_id,
        llamacpp_image_tag=x86_image_tag,
        vllm_image_tag="",
        llamacpp_gguf_paths=x86_gguf_paths,
        vllm_model_ref=config.hf_model_id,
        prompts=config.prompts,
        concurrency=config.concurrency,
        accuracy_scores=accuracy_scores,
    )
    baseline_result = make_trial_evaluator(baseline_ctx)(winner_config)
    on_event("benchmark", "completed", {})

    # --- Report ---
    on_event("report", "running", {})
    probe = BackendProbeResult(
        backend=winner_config.backend,
        concurrency=config.concurrency,
        tokens_per_second=winner_result.throughput.tokens_per_second,
        p95_latency_ms=winner_result.latency_ms.p95,
        ttft_p50_ms=winner_result.latency_ms.ttft_p50,
        accuracy_score=winner_result.accuracy_score,
        cost_per_1m_tokens=winner_result.cost_per_1m_tokens,
    )
    selection = select_backend([probe], config.sla_accuracy_floor, config.sla_p95_latency_ms)

    report_inputs = MigrationReportInputs(
        workload_name=config.workload_name,
        model_ref=config.hf_model_id,
        commit_sha=config.commit_sha,
        baseline=baseline_result,
        winner=winner_result,
        winner_config=winner_config,
        backend_justification=selection.justification,
        accuracy_floor=config.sla_accuracy_floor,
        latency_sla_ms=config.sla_p95_latency_ms,
        search_trial_count=len(study.trials),
        analysis_blockers=analysis.blockers,
        optimizations_applied=_describe_optimizations(winner_config),
    )
    report_markdown = render_migration_report(report_inputs)
    on_event("report", "completed", {})

    trials = [
        TrialSummary(
            trial_number=i,
            backend=tc.backend,
            quant=tc.quant,
            threads=tc.threads,
            core_pinning=tc.core_pinning,
            batch_size=tc.batch_size,
            kv_cache_precision=tc.kv_cache_precision,
            context_length=tc.context_length,
            tokens_per_second=br.throughput.tokens_per_second,
            p95_latency_ms=br.latency_ms.p95,
            cost_per_1m_tokens=br.cost_per_1m_tokens,
            accuracy_score=br.accuracy_score,
            feasible=(
                br.accuracy_score >= config.sla_accuracy_floor
                and br.latency_ms.p95 <= config.sla_p95_latency_ms
            ),
        )
        for i, (tc, br) in enumerate(trial_history)
    ]

    return PipelineResult(
        analysis=analysis,
        baseline_result=baseline_result,
        winner_result=winner_result,
        winner_config=winner_config,
        backend_justification=selection.justification,
        report_markdown=report_markdown,
        trials=trials,
    )
