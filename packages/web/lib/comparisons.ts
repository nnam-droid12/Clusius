import type { BenchmarkResult } from "./types";

export function costDeltaPct(baseline: BenchmarkResult, winner: BenchmarkResult): number {
  return (
    ((baseline.cost_per_1m_tokens - winner.cost_per_1m_tokens) / baseline.cost_per_1m_tokens) * 100
  );
}

export function dollarsSavedPer1M(baseline: BenchmarkResult, winner: BenchmarkResult): number {
  return baseline.cost_per_1m_tokens - winner.cost_per_1m_tokens;
}

// Positive = faster on the Arm winner, matching costDeltaPct's "positive = better" convention
// used throughout the dashboard (the generated report's raw (winner-baseline)/baseline delta
// is signed the other way — negative for a latency/cost reduction — which is the right
// convention for a report read top-to-bottom, just not for a dashboard tile).
export function throughputDeltaPct(baseline: BenchmarkResult, winner: BenchmarkResult): number {
  return (
    ((winner.throughput.tokens_per_second - baseline.throughput.tokens_per_second) /
      baseline.throughput.tokens_per_second) *
    100
  );
}

export function latencyReductionPct(baseline: BenchmarkResult, winner: BenchmarkResult): number {
  return ((baseline.latency_ms.p95 - winner.latency_ms.p95) / baseline.latency_ms.p95) * 100;
}

export function fmt(n: number, digits = 1): string {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
