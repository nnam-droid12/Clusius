"""Renders the per-run `MIGRATION_REPORT.md` from the analyze/migrate/tune/benchmark
stage outputs, and writes it alongside the schema-conformant `result.json` for the
winning Arm configuration. This is the final pipeline stage (§2.5 of the build brief):
baseline -> changes -> chosen config + why -> results table -> Pareto chart -> deltas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from clusius_core.analyze.scanner import Finding
from clusius_core.models import BenchmarkResult, utcnow
from clusius_core.tune.search_space import TrialConfig

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_TEMPLATE_DIR),
    autoescape=select_autoescape(enabled_extensions=(), default=False),
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass
class MigrationReportInputs:
    workload_name: str
    model_ref: str
    commit_sha: str
    baseline: BenchmarkResult
    winner: BenchmarkResult
    winner_config: TrialConfig
    backend_justification: str
    accuracy_floor: float
    latency_sla_ms: float
    search_trial_count: int
    analysis_blockers: list[Finding] = field(default_factory=list)
    optimizations_applied: list[str] = field(default_factory=list)
    pareto_chart_path: str | None = None
    cost_chart_path: str | None = None


def _pct_delta(baseline: float, winner: float) -> float:
    if baseline == 0:
        return 0.0
    return (winner - baseline) / baseline * 100


def render_migration_report(inputs: MigrationReportInputs) -> str:
    template = _env.get_template("migration_report.md.jinja")
    return template.render(
        workload_name=inputs.workload_name,
        model_ref=inputs.model_ref,
        commit_sha=inputs.commit_sha,
        generated_at=utcnow().isoformat(),
        baseline=inputs.baseline,
        winner=inputs.winner,
        winner_config=inputs.winner_config,
        analysis_blockers=inputs.analysis_blockers,
        optimizations_applied=inputs.optimizations_applied,
        backend_justification=inputs.backend_justification,
        throughput_delta_pct=_pct_delta(
            inputs.baseline.throughput.tokens_per_second, inputs.winner.throughput.tokens_per_second
        ),
        latency_delta_pct=_pct_delta(inputs.baseline.latency_ms.p95, inputs.winner.latency_ms.p95),
        cost_delta_pct=_pct_delta(
            inputs.baseline.cost_per_1m_tokens, inputs.winner.cost_per_1m_tokens
        ),
        accuracy_delta_pp=(inputs.winner.accuracy_score - inputs.baseline.accuracy_score) * 100,
        accuracy_floor=inputs.accuracy_floor,
        latency_sla_ms=inputs.latency_sla_ms,
        search_trial_count=inputs.search_trial_count,
        pareto_chart_path=inputs.pareto_chart_path,
        cost_chart_path=inputs.cost_chart_path,
    )


def write_migration_report(inputs: MigrationReportInputs, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "MIGRATION_REPORT.md"
    path.write_text(render_migration_report(inputs), encoding="utf-8")
    return path
