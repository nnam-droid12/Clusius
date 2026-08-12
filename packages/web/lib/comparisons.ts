import type { BenchmarkResult, RunSummary } from "./types";

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

export interface ComparableRun {
  run: RunSummary;
  baseline: BenchmarkResult;
  winner: BenchmarkResult;
  throughputPct: number;
  latencyPct: number;
  /** null when the baseline has no configured $/hr — "not priced," not "free." */
  costPct: number | null;
}

function findResult(run: RunSummary, kind: string): BenchmarkResult | undefined {
  return run.results.find((r) => r.kind === kind)?.result_json;
}

/** Every completed run with a full baseline-vs-winner comparison, sorted by measured
 * throughput gain descending — the one place this filter+shape logic lives, since both
 * the results gallery and the savings calculator need exactly the same real rows. */
export function comparableRuns(results: RunSummary[]): ComparableRun[] {
  return results
    .map((run): ComparableRun | null => {
      const baseline = findResult(run, "baseline_x86");
      const winner = findResult(run, "arm_winner");
      if (!baseline || !winner) return null;
      return {
        run,
        baseline,
        winner,
        throughputPct: throughputDeltaPct(baseline, winner),
        latencyPct: latencyReductionPct(baseline, winner),
        costPct: baseline.cost_per_1m_tokens > 0 ? costDeltaPct(baseline, winner) : null,
      };
    })
    .filter((row): row is ComparableRun => row !== null)
    .sort((a, b) => b.throughputPct - a.throughputPct);
}
