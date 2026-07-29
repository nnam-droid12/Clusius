// Mirrors what clusius_api.jobs.tasks.run_pipeline actually executes today. The
// full five-stage vision (+ migrate, + auto-tune) is real in clusius-core but not
// yet wired into the API job — showing stages here that never ran would be exactly
// the kind of fabricated progress Clusius refuses to produce for benchmark numbers.
const STAGES = ["analyze", "benchmark", "done"] as const;
const STAGE_LABELS: Record<(typeof STAGES)[number], string> = {
  analyze: "Analyze",
  benchmark: "Benchmark",
  done: "Report",
};

interface StageTimelineProps {
  currentStage: string | null;
  runStatus: string;
}

function stageState(
  stage: string,
  currentStage: string | null,
  runStatus: string
): "done" | "active" | "pending" | "failed" {
  const currentIndex = currentStage ? STAGES.indexOf(currentStage as (typeof STAGES)[number]) : -1;
  const stageIndex = STAGES.indexOf(stage as (typeof STAGES)[number]);

  if (runStatus === "failed" && stageIndex === currentIndex) return "failed";
  if (stageIndex < currentIndex) return "done";
  if (stageIndex === currentIndex) return runStatus === "completed" ? "done" : "active";
  return "pending";
}

export function StageTimeline({ currentStage, runStatus }: StageTimelineProps) {
  return (
    <div className="flex items-center gap-2">
      {STAGES.map((stage, i) => {
        const state = stageState(stage, currentStage, runStatus);
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
                {state === "done" ? "✓" : i + 1}
              </div>
              <span className={`text-xs ${state === "pending" ? "text-muted" : "text-primary"}`}>
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
