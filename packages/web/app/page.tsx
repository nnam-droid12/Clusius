import Link from "next/link";

import { Nav } from "@/components/Nav";

const STAGES = [
  {
    name: "Analyze",
    detail:
      "Scans the workload for x86-only assumptions — CUDA calls, AVX flags, unpinned base images, x86-only wheels.",
  },
  {
    name: "Migrate",
    detail:
      "Rebuilds for linux/arm64 against two Arm-optimized backends: llama.cpp+KleidiAI and vLLM+oneDNN/ACL.",
  },
  {
    name: "Auto-tune",
    detail:
      "An Optuna NSGA-II search explores quant, threads, batch size, and backend, live on the target — an accuracy floor and latency SLA gate every trial.",
  },
  {
    name: "Benchmark",
    detail:
      "Runs the winning config against the x86 baseline under an identical load profile — same prompts, same concurrency.",
  },
  {
    name: "Report",
    detail:
      "Emits a migration report explaining what changed and why, plus a schema-conformant result.json.",
  },
];

const PRINCIPLES = [
  {
    title: "Every number is measured",
    body: "No mocked benchmark results, ever. If a value is in a report, it came from a real request against a real endpoint.",
  },
  {
    title: "The search is auditable",
    body: "Every trial Optuna runs — config and measured metrics — is persisted, so the Pareto frontier can be replayed, not just trusted.",
  },
  {
    title: "The reasoning is visible",
    body: "Backend selection isn't 'run both, keep the bigger number' — Clusius states which backend won, at what concurrency, and why.",
  },
  {
    title: "Bring your own hardware",
    body: "Target mode drives an existing C4A + x86 pair over SSH. Clusius never needs to hold your cloud credentials.",
  },
];

export default function HomePage() {
  return (
    <div className="min-h-screen">
      <Nav />

      <section className="mx-auto max-w-4xl px-6 py-24 text-center">
        <p className="text-sm font-medium uppercase tracking-wider text-series-1">
          Arm Create: AI Optimization Challenge
        </p>
        <h1 className="mt-4 text-5xl font-semibold tracking-tight sm:text-6xl">
          Migrate to Arm64. <span className="text-series-1">Prove it&apos;s faster.</span>
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-secondary">
          Clusius is an agent that migrates an x86 AI-inference workload to Google Axion (C4A),
          applies Arm-specific optimizations, and searches the configuration space on the live
          instance until it converges on the cost/latency-optimal setup for your SLA — then hands
          you a reproducible benchmark and a migration report with the receipts.
        </p>
        <div className="mt-10 flex items-center justify-center gap-4">
          <Link
            href="/runs/new"
            className="rounded-md bg-series-1 px-5 py-3 text-sm font-medium text-white transition-opacity hover:opacity-90"
          >
            Launch a run
          </Link>
          <Link
            href="/runs"
            className="rounded-md border border-border px-5 py-3 text-sm font-medium hover:bg-surface"
          >
            View run history
          </Link>
        </div>
      </section>

      <section className="border-t border-border bg-surface py-20">
        <div className="mx-auto max-w-6xl px-6">
          <h2 className="text-sm font-medium uppercase tracking-wider text-muted">The pipeline</h2>
          <div className="mt-6 grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
            {STAGES.map((stage, i) => (
              <div key={stage.name} className="rounded-lg border border-border bg-page p-5">
                <div className="tabular-nums text-sm text-muted">
                  {String(i + 1).padStart(2, "0")}
                </div>
                <div className="mt-2 font-semibold">{stage.name}</div>
                <p className="mt-2 text-sm leading-relaxed text-secondary">{stage.detail}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-20">
        <h2 className="text-sm font-medium uppercase tracking-wider text-muted">
          Design principles
        </h2>
        <div className="mt-6 grid gap-8 sm:grid-cols-2">
          {PRINCIPLES.map((p) => (
            <div key={p.title}>
              <h3 className="font-semibold">{p.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-secondary">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-t border-border py-20">
        <div className="mx-auto max-w-3xl px-6 text-center">
          <h2 className="text-2xl font-semibold tracking-tight">See it run on your own hardware</h2>
          <p className="mt-3 text-secondary">
            Point Clusius at an existing C4A + x86 instance pair over SSH and watch the pipeline run
            live, or explore the code and open benchmark schema on GitHub.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Link
              href="/runs/new"
              className="rounded-md bg-series-1 px-5 py-3 text-sm font-medium text-white transition-opacity hover:opacity-90"
            >
              Launch a run
            </Link>
            <a
              href="https://github.com/nnam-droid12/Clusius"
              target="_blank"
              rel="noreferrer"
              className="rounded-md border border-border px-5 py-3 text-sm font-medium hover:bg-surface"
            >
              Read the source
            </a>
          </div>
        </div>
      </section>

      <footer className="border-t border-border py-8 text-center text-sm text-muted">
        Clusius · Apache-2.0 ·{" "}
        <a href="https://github.com/nnam-droid12/Clusius" className="hover:text-primary">
          github.com/nnam-droid12/Clusius
        </a>
      </footer>
    </div>
  );
}
