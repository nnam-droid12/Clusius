"use client";

import Link from "next/link";

import { Nav } from "@/components/Nav";
import { comparableRuns, fmt } from "@/lib/comparisons";
import { useResults } from "@/lib/hooks";

export default function ResultsGalleryPage() {
  const { data: results, isLoading, error } = useResults();

  const rows = comparableRuns(results ?? []);
  const incomplete = (results ?? []).length - rows.length;

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-5xl px-6 py-12">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Results gallery</h1>
            <p className="mt-1 text-sm text-secondary">
              Every completed migration Clusius has run, real and independently checkable — not
              one cherry-picked demo. Sorted by measured throughput gain.
            </p>
          </div>
          <Link href="/savings" className="text-sm font-medium text-series-1 hover:underline">
            Savings calculator →
          </Link>
        </div>

        {isLoading && <p className="mt-8 text-secondary">Loading results…</p>}
        {error && (
          <p className="mt-8 text-critical">
            Couldn&apos;t reach the Clusius API. Is it running at {process.env.NEXT_PUBLIC_API_URL}?
          </p>
        )}
        {results && rows.length === 0 && !isLoading && (
          <p className="mt-8 text-secondary">
            No completed migrations with a baseline-vs-winner comparison yet — launch a run to see
            it here once it finishes.
          </p>
        )}

        {rows.length > 0 && (
          <div className="mt-8 overflow-hidden rounded-lg border border-border">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface-2 text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Model</th>
                  <th className="px-4 py-3 font-medium">Backend</th>
                  <th className="tabular-nums px-4 py-3 font-medium">Throughput</th>
                  <th className="tabular-nums px-4 py-3 font-medium">p95 latency</th>
                  <th className="tabular-nums px-4 py-3 font-medium">Cost / 1M</th>
                  <th className="tabular-nums px-4 py-3 font-medium">Accuracy</th>
                  <th className="px-4 py-3 font-medium">Run</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ run, baseline, winner, throughputPct, latencyPct, costPct }) => (
                  <tr key={run.id} className="border-t border-border hover:bg-surface">
                    <td className="px-4 py-3">
                      <div className="font-medium text-primary">{run.model_ref}</div>
                      <div className="text-xs text-muted">{run.workload_name}</div>
                    </td>
                    <td className="px-4 py-3 text-secondary">{run.selected_backend ?? "—"}</td>
                    <td className="tabular-nums px-4 py-3">
                      <span className="font-medium text-good">+{fmt(throughputPct)}%</span>
                      <span className="ml-1.5 text-xs text-muted">
                        ({fmt(baseline.throughput.tokens_per_second)} → {fmt(winner.throughput.tokens_per_second)} tok/s)
                      </span>
                    </td>
                    <td className="tabular-nums px-4 py-3">
                      <span className="font-medium text-good">−{fmt(latencyPct)}%</span>
                    </td>
                    <td className="tabular-nums px-4 py-3">
                      {costPct !== null ? (
                        <span className="font-medium text-good">+{fmt(costPct)}%</span>
                      ) : (
                        <span className="text-muted">not priced</span>
                      )}
                    </td>
                    <td className="tabular-nums px-4 py-3 text-secondary">
                      {(winner.accuracy_score * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/runs/${run.id}`}
                        className="font-medium text-series-1 hover:underline"
                      >
                        {run.id.slice(0, 8)}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {incomplete > 0 && (
          <p className="mt-4 text-xs text-muted">
            {incomplete} completed run{incomplete === 1 ? "" : "s"} without a full baseline-vs-winner
            comparison (e.g. analyze-only) not shown here.
          </p>
        )}
      </div>
    </div>
  );
}
