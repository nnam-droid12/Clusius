interface StatTileProps {
  label: string;
  value: string;
  delta?: { text: string; good: boolean };
  accent?: "series-1" | "series-2";
}

export function StatTile({ label, value, delta, accent }: StatTileProps) {
  return (
    <div className="rounded-lg border border-border bg-surface p-5">
      <div className="text-sm text-secondary">{label}</div>
      <div
        className="tabular-nums mt-1 text-3xl font-semibold"
        style={accent ? { color: `var(--${accent})` } : undefined}
      >
        {value}
      </div>
      {delta && (
        <div className={`mt-1 text-sm ${delta.good ? "text-success-text" : "text-critical"}`}>
          {delta.text}
        </div>
      )}
    </div>
  );
}
