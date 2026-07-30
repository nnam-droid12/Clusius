"use client";

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
} from "recharts";

import type { Trial } from "@/lib/types";

interface ParetoChartProps {
  trials: Trial[];
}

export function ParetoChart({ trials }: ParetoChartProps) {
  const feasible = trials.filter((t) => t.feasible);
  const infeasible = trials.filter((t) => !t.feasible);

  return (
    <ResponsiveContainer width="100%" height={360}>
      <ScatterChart margin={{ top: 16, right: 16, bottom: 16, left: 0 }}>
        <CartesianGrid stroke="var(--gridline)" />
        <XAxis
          type="number"
          dataKey="cost_per_1m_tokens"
          name="cost per 1M tokens"
          unit="$"
          stroke="var(--text-muted)"
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
        />
        <YAxis
          type="number"
          dataKey="tokens_per_second"
          name="throughput"
          unit=" tok/s"
          stroke="var(--text-muted)"
          tick={{ fill: "var(--text-muted)", fontSize: 12 }}
        />
        <ZAxis range={[80, 80]} />
        <Tooltip
          cursor={{ strokeDasharray: "3 3" }}
          contentStyle={{
            backgroundColor: "var(--surface)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={(value: number, name: string) => [
            name === "cost per 1M tokens" ? `$${value.toFixed(4)}` : `${value.toFixed(1)} tok/s`,
            name,
          ]}
        />
        <Legend wrapperStyle={{ fontSize: 12 }} />
        <Scatter
          name="infeasible (violates SLA / accuracy floor)"
          data={infeasible}
          fill="var(--baseline)"
        />
        <Scatter name="feasible" data={feasible} fill="var(--series-1)" />
      </ScatterChart>
    </ResponsiveContainer>
  );
}
