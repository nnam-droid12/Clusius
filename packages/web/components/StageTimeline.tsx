import type { RunDetail, RunEvent } from "@/lib/types";

// The full pipeline (analyze -> migrate -> tune -> benchmark -> report -> done) runs
// for real when the API has SSH targets configured (see clusius_api.jobs.tasks); the
// fallback path only ever emits analyze -> benchmark -> done. Redis pub/sub events
// are ephemeral — they're only available while a run is actively being watched, not
// after a page reload — so state is derived two ways: from the live SSE event
// history while the run is still in progress, and from persisted `run` fields
// (`selected_backend`, `results`) once it's terminal. Either way, a stage that never
// ran shows as skipped rather than being fabricated as "done".
const STAGES = ["analyze", "migrate", "tune", "benchmark", "report", "done"] as const;
const STAGE_LABELS: Record<(typeof STAGES)[number], string> = {
  analyze: "Analyze",
  migrate: "Migrate",
  tune: "Auto-tune",
  benchmark: "Benchmark",
  report: "Report",
  done: "Done",
};

interface StageTimelineProps {
  run: RunDetail;
  events: RunEvent[];
}

type StageState = "done" | "active" | "pending" | "failed" | "skipped";

function statesFromLiveEvents(events: RunEvent[]): Record<string, StageState> {
  const states: Record<string, StageState> = Object.fromEntries(STAGES.map((s) => [s, "pending"]));
  for (const event of events) {
    if (!event.stage || !(event.stage in states)) continue;
    if (event.status === "completed") states[event.stage] = "done";
    else if (event.status === "failed") states[event.stage] = "failed";
    else if (states[event.stage] !== "done") states[event.stage] = "active";
  }
  return states;
}

function statesFromPersistedRun(run: RunDetail): Record<string, StageState> {
  const ranFullPipeline = run.selected_backend != null;
  const hasBaselineResult = run.results.some((r) => r.kind === "baseline_x86");
  const states: Record<string, StageState> = Object.fromEntries(STAGES.map((s) => [s, "skipped"]));

  states.analyze = "done";
  if (ranFullPipeline) {
    for (const stage of STAGES) states[stage] = "done";
  } else {
    states.benchmark = hasBaselineResult ? "done" : "skipped";
    states.done = "done";
  }

  if (run.status === "failed") {
    const lastDone = [...STAGES].reverse().find((s) => states[s] === "done");
    // Best guess at the failure point: the stage after the last one we can prove
    // completed, from the persisted record alone (no per-stage failure detail once
    // the live event stream is gone).
    const idx = lastDone ? STAGES.indexOf(lastDone) + 1 : 0;
    if (STAGES[idx]) states[STAGES[idx]] = "failed";
  }

  return states;
}

export function StageTimeline({ run, events }: StageTimelineProps) {
  const isTerminal = run.status === "completed" || run.status === "failed";
  const states =
    isTerminal && events.length <= 1 ? statesFromPersistedRun(run) : statesFromLiveEvents(events);

  return (
    <div className="flex items-center gap-2">
      {STAGES.map((stage, i) => {
        const state = states[stage];
        return (
          <div key={stage} className="flex flex-1 items-center gap-2">
            <div className="flex flex-1 flex-col items-center gap-2">
              <div
                className={`flex h-8 w-8 items-center justify-center rounded-full text-xs font-semibold ${
                  state === "done"
                    ? "bg-good text-white"
                    : state === "active"
                      ? "bg-series-1 text-white"
                      : state === "failed"
                        ? "bg-critical text-white"
                        : "border border-border bg-surface text-muted"
                }`}
              >
                {state === "done" ? "✓" : state === "skipped" ? "–" : i + 1}
              </div>
              <span
                className={`text-xs ${
                  state === "pending" || state === "skipped" ? "text-muted" : "text-primary"
                }`}
              >
                {STAGE_LABELS[stage]}
              </span>
            </div>
            {i < STAGES.length - 1 && <div className="mb-5 h-px flex-1 bg-gridline" />}
          </div>
        );
      })}
    </div>
  );
}
