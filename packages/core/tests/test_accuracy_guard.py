import pytest
from clusius_core.tune.accuracy_guard import (
    AccuracyGuard,
    AccuracyGuardConfig,
    EvalCase,
    exact_match_score,
)


def test_exact_match_score_all_correct() -> None:
    cases = [EvalCase(prompt="2+2", expected="4"), EvalCase(prompt="1+1", expected="2")]

    score = exact_match_score(cases, predict=lambda p: {"2+2": "4", "1+1": "2"}[p])

    assert score == 1.0


def test_exact_match_score_partial() -> None:
    cases = [EvalCase(prompt="2+2", expected="4"), EvalCase(prompt="1+1", expected="2")]

    score = exact_match_score(cases, predict=lambda p: {"2+2": "4", "1+1": "wrong"}[p])

    assert score == 0.5


def test_exact_match_score_rejects_empty_eval_set() -> None:
    with pytest.raises(ValueError):
        exact_match_score([], predict=lambda p: p)


def test_guard_passes_above_floor() -> None:
    guard = AccuracyGuard(AccuracyGuardConfig(floor_fraction=0.9))
    guard.set_baseline(1.0)

    assert guard.passes(0.95)
    assert guard.passes(0.90)


def test_guard_rejects_below_floor() -> None:
    guard = AccuracyGuard(AccuracyGuardConfig(floor_fraction=0.9))
    guard.set_baseline(1.0)

    assert not guard.passes(0.85)


def test_guard_requires_baseline_before_passes() -> None:
    guard = AccuracyGuard()

    with pytest.raises(RuntimeError):
        guard.passes(0.9)


def test_guard_caches_score_per_model_quant() -> None:
    guard = AccuracyGuard()
    calls = []

    def compute() -> float:
        calls.append(1)
        return 0.9

    first = guard.score_for("qwen2.5-7b", "Q4_K_M", compute)
    second = guard.score_for("qwen2.5-7b", "Q4_K_M", compute)

    assert first == second == 0.9
    assert len(calls) == 1


def test_guard_does_not_share_cache_across_quants() -> None:
    guard = AccuracyGuard()

    guard.score_for("qwen2.5-7b", "Q8_0", lambda: 0.95)
    guard.score_for("qwen2.5-7b", "Q4_0", lambda: 0.80)

    assert guard.score_for("qwen2.5-7b", "Q8_0", lambda: 0.0) == 0.95
    assert guard.score_for("qwen2.5-7b", "Q4_0", lambda: 0.0) == 0.80
