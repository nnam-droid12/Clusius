"""The agentic search loop: Optuna's NSGA-II multi-objective sampler searches the
bounded config space (search_space.py), evaluating each candidate on the real target
via an injected `evaluate` callback, subject to the accuracy floor and latency SLA as
hard constraints (Optuna's `constraints_func` mechanism — a trial that violates either
is pushed out of the Pareto-optimal set rather than silently scored as if it were
fine). Every trial is persisted on the returned `optuna.Study`, so the full search is
auditable and the Pareto frontier can be plotted after the fact.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

import optuna

from clusius_core.models import BenchmarkResult
from clusius_core.tune.search_space import SearchSpace, TrialConfig, suggest_trial

optuna.logging.set_verbosity(optuna.logging.WARNING)

TrialEvaluator = Callable[[TrialConfig], BenchmarkResult]


@dataclass
class TunerConfig:
    max_trials: int
    accuracy_floor: float
    latency_sla_ms: float
    max_wall_clock_s: float | None = None
    seed: int | None = None


def _constraints_func(trial: optuna.trial.FrozenTrial) -> tuple[float, float]:
    return cast(tuple[float, float], trial.user_attrs["constraint"])


def run_search(
    space: SearchSpace,
    config: TunerConfig,
    evaluate: TrialEvaluator,
    study: optuna.Study | None = None,
) -> optuna.Study:
    if study is None:
        sampler = optuna.samplers.NSGAIISampler(
            seed=config.seed, constraints_func=_constraints_func
        )
        study = optuna.create_study(directions=["maximize", "minimize"], sampler=sampler)

    def objective(trial: optuna.Trial) -> tuple[float, float]:
        trial_config = suggest_trial(trial, space)
        result = evaluate(trial_config)

        accuracy_violation = config.accuracy_floor - result.accuracy_score
        latency_violation = result.latency_ms.p95 - config.latency_sla_ms
        trial.set_user_attr("constraint", (accuracy_violation, latency_violation))
        trial.set_user_attr("accuracy_score", result.accuracy_score)
        trial.set_user_attr("p95_latency_ms", result.latency_ms.p95)
        trial.set_user_attr("cost_per_1m_tokens", result.cost_per_1m_tokens)
        trial.set_user_attr("backend", result.backend)
        trial.set_user_attr("quant", result.quant)

        return result.throughput.tokens_per_second, result.cost_per_1m_tokens

    study.optimize(objective, n_trials=config.max_trials, timeout=config.max_wall_clock_s)
    return study


def feasible_trials(study: optuna.Study) -> list[optuna.trial.FrozenTrial]:
    """Completed trials that satisfied both constraints (accuracy floor + latency SLA)."""
    feasible = []
    for trial in study.trials:
        if trial.state != optuna.trial.TrialState.COMPLETE:
            continue
        violations = trial.user_attrs.get("constraint")
        if violations is not None and all(v <= 0 for v in violations):
            feasible.append(trial)
    return feasible


def pareto_frontier(study: optuna.Study) -> list[optuna.trial.FrozenTrial]:
    """The feasible trials on the Pareto frontier (best_trials already restricts to
    non-dominated trials among those Optuna considers valid under the constraints)."""
    feasible_numbers = {t.number for t in feasible_trials(study)}
    return [t for t in study.best_trials if t.number in feasible_numbers]
