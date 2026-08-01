"use client";

import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
  LabelList,
} from "recharts";

import { fmt } from "@/lib/comparisons";
import type { BenchmarkResult, Trial } from "@/lib/types";

interface ParetoChartProps {
  trials: Trial[];
  winnerResult?: BenchmarkResult;
}

// The winner isn't a flagged row in the DB — it's whichever trial's config matches the
// persisted arm_winner result exactly (report.py builds that result directly from the
// winning TrialConfig, so this match is exact, not a heuristic).
function isWinnerTrial(trial: Trial, winner?: BenchmarkResult): boolean {
  if (!winner) return false;
  return (
    trial.backend === winner.backend &&
    trial.quant === winner.quant &&
    trial.threads === winner.threads &&
    trial.batch_size === winner.batch_size &&
    trial.kv_cache_precision === winner.kv_cache_precision &&
    trial.core_pinning === winner.core_pinning &&
    trial.context_length === winner.context_length
  );
}

function TrialTooltip({ active, payload }: { active?: boolean; payload?: { payload: Trial }[] }) {
  if (!active || !payload || payload.length === 0) return null;
  const first = payload[0];
  if (!first) return null;
  const t = first.payload;
  return (
    <div className="rounded-lg border border-border bg-surface px-3 py-2 text-xs shadow-sm">
      <div className="font-medium text-primary">
        Trial #{t.trial_number} · {t.backend} {t.quant}
      </div>
      <div className="mt-1.5 space-y-0.5 text-secondary">
        <div>Throughput: {fmt(t.tokens_per_second)} tok/s</div>
        <div>p95 latency: {fmt(t.p95_latency_ms, 0)} ms</div>
        <div>Cost: ${fmt(t.cost_per_1m_tokens, 4)} / 1M tokens</div>
        <div>Accuracy: {(t.accuracy_score * 100).toFixed(1)}%</div>
        <div className="text-muted">
          threads {t.threads} · batch {t.batch_size} · kv {t.kv_cache_precision} ·{" "}
          {t.core_pinning ? "pinned" : "unpinned"} · ctx {t.context_length}
        </div>
        {!t.feasible && <div className="mt-1 text-critical">violates SLA / accuracy floor</div>}
      </div>
    </div>
  );
}

function TrialTable({ trials, winnerResult }: ParetoChartProps) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-border text-secondary">
            <th className="py-2 pr-3 font-medium">#</th>
            <th className="py-2 pr-3 font-medium">Backend</th>
            <th className="py-2 pr-3 font-medium">Quant</th>
            <th className="py-2 pr-3 font-medium">Threads</th>
            <th className="py-2 pr-3 font-medium">Batch</th>
            <th className="py-2 pr-3 font-medium">KV cache</th>
            <th className="py-2 pr-3 font-medium">Pinned</th>
            <th className="tabular-nums py-2 pr-3 font-medium">tok/s</th>
            <th className="tabular-nums py-2 pr-3 font-medium">p95 ms</th>
            <th className="tabular-nums py-2 pr-3 font-medium">$/1M</th>
            <th className="tabular-nums py-2 pr-3 font-medium">Accuracy</th>
            <th className="py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {trials.map((t) => {
            const winner = isWinnerTrial(t, winnerResult);
            return (
              <tr key={t.id} className="border-b border-border last:border-0">
                <td className="py-2 pr-3 text-secondary">{t.trial_number}</td>
                <td className="py-2 pr-3">{t.backend}</td>
                <td className="py-2 pr-3">{t.quant}</td>
                <td className="py-2 pr-3">{t.threads}</td>
                <td className="py-2 pr-3">{t.batch_size}</td>
                <td className="py-2 pr-3">{t.kv_cache_precision}</td>
                <td className="py-2 pr-3">{t.core_pinning ? "yes" : "no"}</td>
                <td className="tabular-nums py-2 pr-3">{fmt(t.tokens_per_second)}</td>
                <td className="tabular-nums py-2 pr-3">{fmt(t.p95_latency_ms, 0)}</td>
                <td className="tabular-nums py-2 pr-3">{fmt(t.cost_per_1m_tokens, 4)}</td>
                <td className="tabular-nums py-2 pr-3">{(t.accuracy_score * 100).toFixed(1)}%</td>
                <td className="py-2">
                  {winner ? (
                    <span className="rounded-full bg-good/10 px-2 py-0.5 font-medium text-good">
                      winner
                    </span>
                  ) : t.feasible ? (
                    <span className="text-secondary">feasible</span>
                  ) : (
                    <span className="text-critical">infeasible</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function ParetoChart({ trials, winnerResult }: ParetoChartProps) {
  const [view, setView] = useState<"chart" | "table">("chart");

  const { infeasible, feasible, winner } = useMemo(() => {
    const winnerTrial = trials.find((t) => isWinnerTrial(t, winnerResult));
    return {
      infeasible: trials.filter((t) => !t.feasible),
      feasible: trials.filter((t) => t.feasible && t.id !== winnerTrial?.id),
      winner: winnerTrial ? [winnerTrial] : [],
    };
  }, [trials, winnerResult]);

  const costVaries = new Set(trials.map((t) => t.cost_per_1m_tokens)).size > 1;

  return (
    <div>
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted">
          {feasible.length + winner.length} feasible · {infeasible.length} infeasible · bubble
          size ∝ p95 latency (larger = slower)
        </p>
        <button
          type="button"
          onClick={() => setView(view === "chart" ? "table" : "chart")}
          className="rounded-md border border-border px-2 py-1 text-xs text-secondary hover:text-primary"
        >
          {view === "chart" ? "View as table" : "View as chart"}
        </button>
      </div>

      {!costVaries && (
        <p className="mt-2 text-xs text-muted">
          Cost per 1M tokens reads $0.00 for every trial because this target pair has no
          configured $/hr — see &ldquo;Known Gaps&rdquo; in the README. Throughput (y-axis) and
          latency (bubble size) are real, live measurements regardless.
        </p>
      )}

      {view === "table" ? (
        <div className="mt-4">
          <TrialTable trials={trials} winnerResult={winnerResult} />
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={380}>
          <ScatterChart margin={{ top: 16, right: 16, bottom: 24, left: 8 }}>
            <CartesianGrid stroke="var(--gridline)" strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="cost_per_1m_tokens"
              name="cost per 1M tokens"
              unit="$"
              stroke="var(--gridline)"
              tick={{ fill: "var(--text-muted)", fontSize: 11 }}
              label={{
                value: "Cost per 1M tokens ($)",
                position: "insideBottom",
                offset: -12,
                fill: "var(--text-muted)",
                fontSize: 12,
              }}
            />
            <YAxis
              type="number"
              dataKey="tokens_per_second"
              name="throughput"
              unit=" tok/s"
              stroke="var(--gridline)"
              tick={{ fill: "var(--text-muted)", fontSize: 11 }}
              label={{
                value: "Throughput (tok/s)",
                angle: -90,
                position: "insideLeft",
                fill: "var(--text-muted)",
                fontSize: 12,
              }}
            />
            <ZAxis type="number" dataKey="p95_latency_ms" range={[64, 420]} name="p95 latency" />
            <Tooltip
              content={<TrialTooltip />}
              cursor={{ strokeDasharray: "3 3", stroke: "var(--gridline)" }}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Scatter
              name="Infeasible (violates SLA / accuracy floor)"
              data={infeasible}
              fill="var(--status-critical)"
              fillOpacity={0.5}
            />
            <Scatter name="Feasible" data={feasible} fill="var(--series-1)" fillOpacity={0.85} />
            <Scatter
              name="Winner"
              data={winner}
              fill="var(--status-good)"
              stroke="var(--surface)"
              strokeWidth={2}
            >
              <LabelList
                content={(props: { x?: string | number; y?: string | number }) => {
                  const x = typeof props.x === "number" ? props.x : Number(props.x ?? 0);
                  const y = typeof props.y === "number" ? props.y : Number(props.y ?? 0);
                  return (
                    <text
                      x={x}
                      y={y - 14}
                      textAnchor="middle"
                      fontSize={11}
                      fontWeight={600}
                      fill="var(--text-primary)"
                    >
                      Winner
                    </text>
                  );
                }}
              />
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
