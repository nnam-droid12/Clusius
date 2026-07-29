"""Backend selection policy (build brief §4): probe both backends on the run's actual
traffic profile, then pick the winner subject to the accuracy floor and latency SLA —
never "run both, keep the bigger number." The justification text is a first-class
output, not a log line, since it's what makes the migration report's reasoning visible.
"""

from __future__ import annotations

from dataclasses import dataclass

from clusius_core.models import Backend

_BACKEND_LABEL = {"llamacpp": "llama.cpp+KleidiAI", "vllm": "vLLM+ACL"}


@dataclass
class BackendProbeResult:
    backend: Backend
    concurrency: int
    tokens_per_second: float
    p95_latency_ms: float
    ttft_p50_ms: float
    accuracy_score: float
    cost_per_1m_tokens: float


@dataclass
class BackendSelection:
    backend: Backend
    winner: BackendProbeResult
    justification: str


def select_backend(
    probes: list[BackendProbeResult],
    accuracy_floor: float,
    latency_sla_ms: float,
) -> BackendSelection:
    if not probes:
        raise ValueError("no backend probes to select from")

    eligible = [
        p
        for p in probes
        if p.accuracy_score >= accuracy_floor and p.p95_latency_ms <= latency_sla_ms
    ]
    if not eligible:
        raise RuntimeError(
            "no backend satisfies the accuracy floor "
            f"({accuracy_floor:.2f}) and latency SLA ({latency_sla_ms:.0f}ms); "
            f"probed: {[(p.backend, p.accuracy_score, p.p95_latency_ms) for p in probes]}"
        )

    winner = max(eligible, key=lambda p: p.tokens_per_second)
    others = [p for p in probes if p is not winner]
    justification = _build_justification(winner, others, accuracy_floor, latency_sla_ms)
    return BackendSelection(backend=winner.backend, winner=winner, justification=justification)


def _build_justification(
    winner: BackendProbeResult,
    others: list[BackendProbeResult],
    accuracy_floor: float,
    latency_sla_ms: float,
) -> str:
    winner_label = _BACKEND_LABEL[winner.backend]
    lines = [
        f"Selected {winner_label}: at your measured concurrency of {winner.concurrency}, "
        f"it delivered "
        f"{winner.tokens_per_second:.1f} tok/s at {winner.accuracy_score:.1%} accuracy "
        f"(floor {accuracy_floor:.1%}) and {winner.p95_latency_ms:.0f}ms p95 latency "
        f"(SLA {latency_sla_ms:.0f}ms)."
    ]
    for other in others:
        other_label = _BACKEND_LABEL[other.backend]
        if other.accuracy_score < accuracy_floor or other.p95_latency_ms > latency_sla_ms:
            reason = []
            if other.accuracy_score < accuracy_floor:
                reason.append(
                    f"accuracy {other.accuracy_score:.1%} fell below the {accuracy_floor:.1%} floor"
                )
            if other.p95_latency_ms > latency_sla_ms:
                reason.append(
                    f"p95 latency {other.p95_latency_ms:.0f}ms exceeded the "
                    f"{latency_sla_ms:.0f}ms SLA"
                )
            lines.append(f"{other_label} was excluded: {'; '.join(reason)}.")
            continue

        delta_pct = (
            (winner.tokens_per_second - other.tokens_per_second) / other.tokens_per_second * 100
        )
        if delta_pct >= 0:
            lines.append(
                f"{other_label} was {abs(delta_pct):.0f}% slower at this concurrency "
                f"(though it had a lower single-stream TTFT of {other.ttft_p50_ms:.0f}ms "
                f"vs {winner.ttft_p50_ms:.0f}ms)."
            )
        else:
            lines.append(
                f"{other_label} was {abs(delta_pct):.0f}% faster but was not selected — see above."
            )

    return " ".join(lines)
