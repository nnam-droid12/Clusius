"""Accuracy guard: runs a small task-appropriate eval set against a candidate config
and rejects it if its score falls below a fraction of the baseline's score, so the
tuner can never silently ship a degraded model in pursuit of throughput/cost.

Eval results are cached per (model, quant) — the accuracy of a given quantized model
doesn't depend on threads/batch/backend-serving details, so there's no reason to
re-run the eval set for every trial that shares a (model, quant) pair.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCase:
    prompt: str
    expected: str


@dataclass
class AccuracyGuardConfig:
    floor_fraction: float = 0.90


def exact_match_score(cases: list[EvalCase], predict: Callable[[str], str]) -> float:
    if not cases:
        raise ValueError("eval set must not be empty")
    correct = sum(1 for case in cases if predict(case.prompt).strip() == case.expected.strip())
    return correct / len(cases)


class AccuracyGuard:
    def __init__(self, config: AccuracyGuardConfig | None = None) -> None:
        self.config = config or AccuracyGuardConfig()
        self._cache: dict[tuple[str, str], float] = {}
        self._baseline_score: float | None = None

    def set_baseline(self, score: float) -> None:
        self._baseline_score = score

    def score_for(self, model: str, quant: str, compute_score: Callable[[], float]) -> float:
        key = (model, quant)
        if key not in self._cache:
            self._cache[key] = compute_score()
        return self._cache[key]

    def passes(self, candidate_score: float) -> bool:
        if self._baseline_score is None:
            raise RuntimeError("baseline score not set; call set_baseline() first")
        return candidate_score >= self._baseline_score * self.config.floor_fraction

    @property
    def floor_score(self) -> float:
        if self._baseline_score is None:
            raise RuntimeError("baseline score not set; call set_baseline() first")
        return self._baseline_score * self.config.floor_fraction
