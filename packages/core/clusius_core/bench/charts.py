"""Matplotlib chart generation for benchmark results: the Pareto frontier from a
tuner search, and a baseline-vs-winner cost/throughput comparison. Kept in `bench/`
(not `report/`) since these charts are useful standalone outputs of a benchmark run,
independent of whether a migration report is ever generated from them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from clusius_core.models import BenchmarkResult


def plot_pareto_frontier(
    trials: list[dict[str, Any]], out_path: Path, winner_index: int | None = None
) -> Path:
    """`trials` is a list of dicts with at least `tokens_per_second`, `cost_per_1m_tokens`,
    and `feasible` keys — the shape produced by summarizing `optuna.trial.FrozenTrial`
    user_attrs. Feasible trials are plotted solid, infeasible ones greyed out."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 5))

    feasible = [t for t in trials if t.get("feasible")]
    infeasible = [t for t in trials if not t.get("feasible")]

    if infeasible:
        ax.scatter(
            [t["cost_per_1m_tokens"] for t in infeasible],
            [t["tokens_per_second"] for t in infeasible],
            c="lightgrey",
            label="infeasible (violates SLA/accuracy floor)",
            zorder=1,
        )
    if feasible:
        ax.scatter(
            [t["cost_per_1m_tokens"] for t in feasible],
            [t["tokens_per_second"] for t in feasible],
            c="steelblue",
            label="feasible",
            zorder=2,
        )

    if winner_index is not None and 0 <= winner_index < len(trials):
        winner = trials[winner_index]
        ax.scatter(
            [winner["cost_per_1m_tokens"]],
            [winner["tokens_per_second"]],
            c="crimson",
            s=140,
            marker="*",
            label="selected config",
            zorder=3,
        )

    ax.set_xlabel("cost per 1M tokens ($)")
    ax.set_ylabel("throughput (tokens/sec)")
    ax.set_title("Auto-tune search: throughput vs. cost")
    ax.legend(loc="best")
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path


def plot_cost_comparison(
    baseline: BenchmarkResult, winner: BenchmarkResult, out_path: Path
) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 4))

    labels = [
        f"x86 baseline\n({baseline.instance_type})",
        f"Arm winner\n({winner.instance_type})",
    ]

    ax1.bar(
        labels,
        [baseline.cost_per_1m_tokens, winner.cost_per_1m_tokens],
        color=["grey", "steelblue"],
    )
    ax1.set_ylabel("cost per 1M tokens ($)")
    ax1.set_title("Cost")

    ax2.bar(
        labels,
        [baseline.throughput.tokens_per_second, winner.throughput.tokens_per_second],
        color=["grey", "steelblue"],
    )
    ax2.set_ylabel("throughput (tokens/sec)")
    ax2.set_title("Throughput")

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    return out_path
