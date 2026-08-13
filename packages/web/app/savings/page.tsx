"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { Nav } from "@/components/Nav";
import { StatTile } from "@/components/StatTile";
import { comparableRuns, fmt } from "@/lib/comparisons";
import { useResults } from "@/lib/hooks";

export default function SavingsCalculatorPage() {
  const { data: results, isLoading, error } = useResults();
  const rows = useMemo(() => comparableRuns(results ?? []), [results]);
  const priced = useMemo(() => rows.filter((r) => r.costPct !== null), [rows]);

  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [monthlySpend, setMonthlySpend] = useState(1000);

  const selected = priced.find((r) => r.run.id === selectedRunId) ?? priced[0];

  const projectedCost =
    selected && selected.costPct !== null
      ? monthlySpend * (1 - selected.costPct / 100)
      : null;
  const savedPerMonth = projectedCost !== null ? monthlySpend - projectedCost : null;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="text-2xl font-semibold tracking-tight">Savings calculator</h1>
        <p className="mt-1 text-sm text-secondary">
          Pick a real, completed Clusius migration and apply its measured cost delta to your own
          spend. This is a projection — it extrapolates one real percentage onto your volume, it
          isn&apos;t a new benchmark of your workload.
        </p>

        {isLoading && <p className="mt-8 text-secondary">Loading real results…</p>}
        {error && (
          <p className="mt-8 text-critical">
            Couldn&apos;t reach the Clusius API. Is it running at {process.env.NEXT_PUBLIC_API_URL}?
          </p>
        )}
        {results && priced.length === 0 && !isLoading && (
          <p className="mt-8 text-secondary">
            No completed run has a priced baseline yet (needs a configured $/hr on the target
            pair) — see the{" "}
            <Link href="/results" className="text-series-1 hover:underline">
              results gallery
            </Link>{" "}
            for real throughput/latency deltas in the meantime.
          </p>
        )}

        {priced.length > 0 && selected && (
          <div className="mt-8 space-y-6">
            <div className="rounded-lg border border-border bg-surface p-6">
              <label className="block text-sm font-medium text-secondary" htmlFor="run-select">
                Base projection on this real run
              </label>
              <select
                id="run-select"
                className="input mt-2"
                value={selected.run.id}
                onChange={(e) => setSelectedRunId(e.target.value)}
              >
                {priced.map((r) => (
                  <option key={r.run.id} value={r.run.id}>
                    {r.run.model_ref} · {r.run.selected_backend} · +{fmt(r.throughputPct)}% tok/s,{" "}
                    {fmt(r.costPct ?? 0)}% cost
                  </option>
                ))}
              </select>
              <Link
                href={`/runs/${selected.run.id}`}
                className="mt-2 inline-block text-xs text-series-1 hover:underline"
              >
                View the underlying evidence for this run →
              </Link>

              <label
                className="mt-6 block text-sm font-medium text-secondary"
                htmlFor="monthly-spend"
              >
                Your current monthly x86 inference spend ($)
              </label>
              <input
                id="monthly-spend"
                type="number"
                min={0}
                step={100}
                className="input mt-2"
                value={monthlySpend}
                onChange={(e) => setMonthlySpend(Math.max(0, Number(e.target.value) || 0))}
              />
              <p className="mt-2 text-xs text-muted">
                Changing this only moves the three dollar figures below — cost scales with your
                volume. Throughput doesn&apos;t: it&apos;s the fixed, real result the selected run
                above measured, not something that gets bigger or smaller based on spend.
              </p>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted">
                Scales with your spend, above
              </p>
              <div className="mt-2 grid grid-cols-1 gap-4 sm:grid-cols-3">
                <StatTile
                  label="Projected Arm cost / mo"
                  value={projectedCost !== null ? `$${fmt(projectedCost, 0)}` : "—"}
                  accent="series-1"
                />
                <StatTile
                  label="Saved / month"
                  value={savedPerMonth !== null ? `$${fmt(savedPerMonth, 0)}` : "—"}
                />
                <StatTile
                  label="Saved / year"
                  value={savedPerMonth !== null ? `$${fmt(savedPerMonth * 12, 0)}` : "—"}
                />
              </div>
            </div>

            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-muted">
                Fixed — from the selected run, not your spend
              </p>
              <div className="mt-2 grid grid-cols-1 gap-4 sm:grid-cols-3">
                <StatTile
                  label="Throughput gain (this run)"
                  value={`+${fmt(selected.throughputPct)}%`}
                  accent="series-1"
                />
              </div>
            </div>

            <p className="text-xs text-muted">
              Projection = your spend × the real measured cost delta from{" "}
              <span className="text-secondary">
                {selected.run.model_ref} ({selected.run.selected_backend})
              </span>
              : {fmt(selected.costPct ?? 0)}% cost, +{fmt(selected.throughputPct)}% throughput,
              −{fmt(selected.latencyPct)}% p95 latency, real GCP on-demand pricing on both sides —
              not a placeholder.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
