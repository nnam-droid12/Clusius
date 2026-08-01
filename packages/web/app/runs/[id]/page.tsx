"use client";

import { useQuery } from "@tanstack/react-query";
import { use } from "react";

import { Nav } from "@/components/Nav";
import { ParetoChart } from "@/components/ParetoChart";
import { ReportViewer } from "@/components/ReportViewer";
import { StageTimeline } from "@/components/StageTimeline";
import { StatTile } from "@/components/StatTile";
import { api } from "@/lib/api-client";
import { costDeltaPct, dollarsSavedPer1M, fmt } from "@/lib/comparisons";
import { useRun } from "@/lib/hooks";
import { useRunEvents } from "@/lib/use-run-events";
import type { BenchmarkResult } from "@/lib/types";

function MoneyShot({ baseline, winner }: { baseline: BenchmarkResult; winner: BenchmarkResult }) {
  const savedPer1M = dollarsSavedPer1M(baseline, winner);
  const costPct = costDeltaPct(baseline, winner);

  return (
    <div className="rounded-lg border border-border bg-surface p-6">
      <h3 className="font-semibold">x86 baseline vs. Arm winner</h3>
      <div className="mt-4 grid grid-cols-2 gap-6">
        <div className="rounded-md border border-border p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-muted">
            x86 baseline · {baseline.instance_type}
          </div>
          <div className="tabular-nums mt-2 text-2xl font-semibold">
            {fmt(baseline.throughput.tokens_per_second)} tok/s
          </div>
          <div className="tabular-nums mt-1 text-sm text-secondary">
            ${fmt(baseline.cost_per_1m_tokens, 4)} / 1M tokens
          </div>
        </div>
        <div className="rounded-md border border-series-1 p-4">
          <div className="text-xs font-medium uppercase tracking-wide text-series-1">
            Arm winner · {winner.instance_type}
          </div>
          <div className="tabular-nums mt-2 text-2xl font-semibold text-series-1">
            {fmt(winner.throughput.tokens_per_second)} tok/s
          </div>
          <div className="tabular-nums mt-1 text-sm text-secondary">
            ${fmt(winner.cost_per_1m_tokens, 4)} / 1M tokens
          </div>
        </div>
      </div>
      <div className="mt-6 text-center">
        <div className="text-sm text-secondary">saved per 1M tokens on Arm</div>
        <div className="tabular-nums mt-1 text-5xl font-semibold text-success-text">
          ${fmt(savedPer1M, 4)}
        </div>
        <div className="tabular-nums mt-1 text-sm text-secondary">
          {fmt(costPct)}% cost reduction
        </div>
      </div>
    </div>
  );
}

export default function RunDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { data: run, isLoading } = useRun(id);
  const events = useRunEvents(id);

  const reportQuery = useQuery({
    queryKey: ["runs", id, "report"],
    queryFn: () => api.getRunReport(id),
    retry: false,
    enabled: run?.status === "completed",
  });

  if (isLoading || !run) {
    return (
      <div className="min-h-screen">
        <Nav />
        <div className="mx-auto max-w-5xl px-6 py-12 text-secondary">Loading run…</div>
      </div>
    );
  }

  const baselineResult = run.results.find((r) => r.kind === "baseline_x86");
  const winnerResult = run.results.find((r) => r.kind === "arm_winner");

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-5xl space-y-8 px-6 py-12">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight">Run {run.id.slice(0, 8)}</h1>
            <span
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${
                run.status === "failed"
                  ? "bg-critical/10 text-critical"
                  : run.status === "completed"
                    ? "bg-good/10 text-good"
                    : "bg-series-1-soft text-series-1"
              }`}
            >
              {run.status}
            </span>
          </div>
          <p className="mt-1 text-sm text-secondary">
            SLA: p95 ≤ {run.sla_p95_latency_ms}ms · accuracy floor{" "}
            {(run.sla_accuracy_floor * 100).toFixed(0)}% · {run.search_budget_trials} trial budget ·{" "}
            {run.target_mode} mode
          </p>
          {run.error_message && <p className="mt-2 text-sm text-critical">{run.error_message}</p>}
        </div>

        <div className="rounded-lg border border-border bg-surface p-6">
          <StageTimeline run={run} events={events} />
        </div>

        {baselineResult && winnerResult && (
          <MoneyShot baseline={baselineResult.result_json} winner={winnerResult.result_json} />
        )}

        {baselineResult && !winnerResult && (
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <StatTile
              label="Throughput"
              value={`${fmt(baselineResult.result_json.throughput.tokens_per_second)} tok/s`}
            />
            <StatTile
              label="p95 latency"
              value={`${fmt(baselineResult.result_json.latency_ms.p95, 0)}ms`}
            />
            <StatTile
              label="Cost / 1M tokens"
              value={`$${fmt(baselineResult.result_json.cost_per_1m_tokens, 4)}`}
            />
            <StatTile
              label="Accuracy"
              value={`${(baselineResult.result_json.accuracy_score * 100).toFixed(1)}%`}
            />
          </div>
        )}

        {run.trials.length > 0 && (
          <div className="rounded-lg border border-border bg-surface p-6">
            <h3 className="font-semibold">Auto-tune search: throughput vs. cost</h3>
            <div className="mt-4">
              <ParetoChart trials={run.trials} winnerResult={winnerResult?.result_json} />
            </div>
          </div>
        )}

        {reportQuery.data && <ReportViewer content={reportQuery.data.content} />}

        {run.artifacts.some((a) => a.kind === "analysis_report") && (
          <p className="text-sm text-secondary">
            An x86-assumption analysis was recorded for this run — see{" "}
            <code className="rounded bg-surface-2 px-1 py-0.5 text-xs">artifacts</code> in the API
            response for the full findings.
          </p>
        )}
      </div>
    </div>
  );
}
