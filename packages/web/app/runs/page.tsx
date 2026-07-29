"use client";

import Link from "next/link";

import { Nav } from "@/components/Nav";
import { useRuns } from "@/lib/hooks";
import type { RunStatus } from "@/lib/types";

const STATUS_COLOR: Record<RunStatus, string> = {
  queued: "text-muted",
  analyze: "text-series-1",
  benchmark: "text-series-1",
  done: "text-good",
  completed: "text-good",
  failed: "text-critical",
};

export default function RunsPage() {
  const { data: runs, isLoading, error } = useRuns();

  return (
    <div className="min-h-screen">
      <Nav />
      <div className="mx-auto max-w-5xl px-6 py-12">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold tracking-tight">Run history</h1>
          <Link
            href="/runs/new"
            className="rounded-md bg-series-1 px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            Launch a run
          </Link>
        </div>

        {isLoading && <p className="mt-8 text-secondary">Loading runs…</p>}
        {error && (
          <p className="mt-8 text-critical">
            Couldn&apos;t reach the Clusius API. Is it running at {process.env.NEXT_PUBLIC_API_URL}?
          </p>
        )}
        {runs && runs.length === 0 && (
          <p className="mt-8 text-secondary">No runs yet. Launch one to see it here.</p>
        )}

        {runs && runs.length > 0 && (
          <div className="mt-8 overflow-hidden rounded-lg border border-border">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface-2 text-muted">
                <tr>
                  <th className="px-4 py-3 font-medium">Run</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Stage</th>
                  <th className="px-4 py-3 font-medium">Target mode</th>
                  <th className="px-4 py-3 font-medium">Created</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((run) => (
                  <tr key={run.id} className="border-t border-border hover:bg-surface">
                    <td className="px-4 py-3">
                      <Link href={`/runs/${run.id}`} className="font-medium text-series-1 hover:underline">
                        {run.id.slice(0, 8)}
                      </Link>
                    </td>
                    <td className={`px-4 py-3 font-medium ${STATUS_COLOR[run.status]}`}>{run.status}</td>
                    <td className="px-4 py-3 text-secondary">{run.stage ?? "—"}</td>
                    <td className="px-4 py-3 text-secondary">{run.target_mode}</td>
                    <td className="tabular-nums px-4 py-3 text-secondary">
                      {new Date(run.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
