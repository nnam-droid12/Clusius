import type { BenchmarkResult } from "./types";

export function costDeltaPct(baseline: BenchmarkResult, winner: BenchmarkResult): number {
  return (
    ((baseline.cost_per_1m_tokens - winner.cost_per_1m_tokens) / baseline.cost_per_1m_tokens) * 100
  );
}

export function dollarsSavedPer1M(baseline: BenchmarkResult, winner: BenchmarkResult): number {
  return baseline.cost_per_1m_tokens - winner.cost_per_1m_tokens;
}

export function fmt(n: number, digits = 1): string {
  return n.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
