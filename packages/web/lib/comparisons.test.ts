import { describe, expect, it } from "vitest";

import { costDeltaPct, dollarsSavedPer1M, fmt } from "./comparisons";
import type { BenchmarkResult } from "./types";

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

describe("fmt", () => {
  it("defaults to one decimal place", () => {
    expect(fmt(3)).toBe("3.0");
  });

  it("respects a custom digit count", () => {
    expect(fmt(1.23456, 4)).toBe("1.2346");
  });
});
