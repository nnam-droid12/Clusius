import { describe, expect, it } from "vitest";

import { comparableRuns, costDeltaPct, dollarsSavedPer1M, fmt } from "./comparisons";
import type { BenchmarkResult, RunSummary } from "./types";

function result(overrides: Partial<BenchmarkResult>): BenchmarkResult {
  return {
    schema_version: "1.0.0",
    run_id: "r1",
    timestamp: "2026-01-01T00:00:00Z",
    commit_sha: "abc123",
    model: "qwen2.5-7b-instruct",
    model_hash: "sha256:test",
    backend: "llamacpp",
    quant: "Q4_K_M",
    instance_type: "c4a-standard-16",
    arch: "aarch64",
    price_per_hour: 0.5,
    threads: 16,
    concurrency: 4,
    throughput: { tokens_per_second: 80, requests_per_second: 2 },
    latency_ms: { ttft_p50: 50, p50: 400, p95: 700, p99: 900 },
    cost_per_1m_tokens: 1.5,
    accuracy_score: 0.95,
    ...overrides,
  };
}

function run(
  id: string,
  results: { kind: string; result_json: BenchmarkResult }[],
  overrides: Partial<RunSummary> = {}
): RunSummary {
  return {
    id,
    status: "completed",
    target_mode: "target",
    selected_backend: "llamacpp",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    workload_name: "showcase-agent",
    model_ref: "qwen2.5-7b-instruct",
    results: results.map((r, i) => ({ id: `${id}-r${i}`, created_at: "2026-01-01T00:00:00Z", ...r })),
    ...overrides,
  };
}

describe("costDeltaPct", () => {
  it("returns positive when the winner is cheaper", () => {
    const baseline = result({ cost_per_1m_tokens: 4.0 });
    const winner = result({ cost_per_1m_tokens: 1.0 });

    expect(costDeltaPct(baseline, winner)).toBeCloseTo(75, 5);
  });

  it("returns negative when the winner is more expensive", () => {
    const baseline = result({ cost_per_1m_tokens: 1.0 });
    const winner = result({ cost_per_1m_tokens: 2.0 });

    expect(costDeltaPct(baseline, winner)).toBeCloseTo(-100, 5);
  });
});

describe("dollarsSavedPer1M", () => {
  it("is the raw dollar difference", () => {
    const baseline = result({ cost_per_1m_tokens: 4.0 });
    const winner = result({ cost_per_1m_tokens: 1.5 });

    expect(dollarsSavedPer1M(baseline, winner)).toBeCloseTo(2.5, 5);
  });
});

describe("comparableRuns", () => {
  it("excludes runs missing a baseline or a winner result", () => {
    const complete = run("a", [
      { kind: "baseline_x86", result_json: result({ throughput: { tokens_per_second: 30, requests_per_second: 1 } }) },
      { kind: "arm_winner", result_json: result({ throughput: { tokens_per_second: 90, requests_per_second: 1 } }) },
    ]);
    const baselineOnly = run("b", [
      { kind: "baseline_x86", result_json: result({}) },
    ]);
    const noResults = run("c", []);

    const rows = comparableRuns([complete, baselineOnly, noResults]);

    expect(rows.map((r) => r.run.id)).toEqual(["a"]);
  });

  it("sorts by throughput gain descending", () => {
    const small = run("small", [
      { kind: "baseline_x86", result_json: result({ throughput: { tokens_per_second: 50, requests_per_second: 1 } }) },
      { kind: "arm_winner", result_json: result({ throughput: { tokens_per_second: 60, requests_per_second: 1 } }) },
    ]);
    const big = run("big", [
      { kind: "baseline_x86", result_json: result({ throughput: { tokens_per_second: 30, requests_per_second: 1 } }) },
      { kind: "arm_winner", result_json: result({ throughput: { tokens_per_second: 120, requests_per_second: 1 } }) },
    ]);

    const rows = comparableRuns([small, big]);

    expect(rows.map((r) => r.run.id)).toEqual(["big", "small"]);
  });

  it("reports costPct as null instead of a fake number when the baseline is unpriced", () => {
    const unpriced = run("unpriced", [
      { kind: "baseline_x86", result_json: result({ cost_per_1m_tokens: 0 }) },
      { kind: "arm_winner", result_json: result({ cost_per_1m_tokens: 0 }) },
    ]);

    const rows = comparableRuns([unpriced]);

    expect(rows).toHaveLength(1);
    expect(rows[0]?.costPct).toBeNull();
  });
});

describe("fmt", () => {
  it("defaults to one decimal place", () => {
    expect(fmt(3)).toBe("3.0");
  });

  it("respects a custom digit count", () => {
    expect(fmt(1.23456, 4)).toBe("1.2346");
  });
});
