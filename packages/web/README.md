# clusius-web

Next.js 15 (App Router) + TypeScript dashboard. Talks only to `clusius-api` over REST
and Server-Sent Events — no direct database access.

Stack: Tailwind, shadcn/ui, Recharts, TanStack Query, Zustand.

## Screens

- **Launch a run** — pick model, target (SSH target-mode or provisioned-mode), SLA,
  search budget, cost ceiling.
- **Live run view** — SSE-streamed stage progress with per-trial updates.
- **Split-screen comparison** — x86 baseline vs. Arm winner running the same showcase
  agent, with a live "$ saved per 1M tokens" counter and throughput gauge.
- **Pareto frontier** — interactive scatter of all trials, winner highlighted.
- **Report viewer** — renders `MIGRATION_REPORT.md` in-app.
- **Run history** — past runs from the API.
