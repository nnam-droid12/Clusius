# Clusius

Clusius is an autonomous agent that migrates an existing x86 AI-inference workload to
Arm64 (Google Axion / C4A), applies Arm-specific optimizations, and searches the
optimization space on the live Arm instance until it converges on the cost/latency-optimal
configuration for a target SLA. It emits a reproducible benchmark, a generated migration
report, and a ready-to-deploy Arm-native artifact.

> **Status: work in progress.** This README will be updated with the headline
> before/after numbers once a full pipeline run against a real C4A + x86 pair has been
> committed to [`bench/results/`](bench/results/). Until then, treat the numbers sections
> below as placeholders.

## What it is

Clusius does not give migration advice — it does the migration and optimization work
itself, on a real instance, and proves every claim with measured numbers. Point it at a
workload (a model + serving config), and it will:

1. **Analyze** the workload for x86-only assumptions.
2. **Migrate** it to Arm64, wiring up two Arm-optimized serving backends.
3. **Auto-tune** a bounded search space (quantization, threads, batch size, backend) on
   the live Arm instance, guarded by an accuracy floor and a latency SLA.
4. **Benchmark** the winning configuration against the x86 baseline, apples-to-apples.
5. **Report** the result as a human-readable migration report and a machine-readable
   `result.json`.

## Headline result

_Pending a real run — see [`bench/results/`](bench/results/) for committed run data as it
lands._

| | x86 baseline | Arm64 (Clusius-optimized) | Delta |
|---|---|---|---|
| Throughput (tok/s) | TBD | TBD | TBD |
| p95 latency (ms) | TBD | TBD | TBD |
| Cost / 1M tokens | TBD | TBD | TBD |
| Accuracy | TBD | TBD | TBD |

## Baseline

Described in full in [`BENCHMARKS.md`](BENCHMARKS.md) once the first real baseline run is
captured.

## Changes made

See the generated `MIGRATION_REPORT.md` from a given run for the exact set of
optimizations applied (KleidiAI, quantization, backend selection, thread/NUMA tuning) and
the reasoning behind each choice.

## Results

Full tables, charts, and links to raw `result.json` files live in
[`bench/results/`](bench/results/) as runs are committed.

## Why it matters

Migrating an AI-inference workload to Arm today means hand-tuning quantization, kernel
libraries, and serving stack choices with no systematic way to prove the result is
actually better. Clusius packages that work into a reusable agent, a reproducible
benchmark harness, and an open result schema so other teams don't have to redo it from
scratch.

## Setup / run / validate on Arm64

### Target mode (default, recommended for reviewers)

Target mode drives an already-running C4A instance and a matched x86 baseline over SSH —
Clusius never needs cloud credentials.

```bash
make setup
cp .env.example .env   # fill in SSH targets for your C4A + x86 pair
make dev               # starts postgres, redis, api, web
```

Then launch a run from the dashboard at `http://localhost:3000`, or via the API:

```bash
curl -X POST http://localhost:8000/runs -H 'content-type: application/json' -d @configs/demo-run.json
```

### Provisioned mode (opt-in)

Provisioned mode has Clusius create the C4A + x86 pair itself via
`google-cloud-compute`, enforcing a configurable cost ceiling and a hard TTL
auto-teardown. Disabled by default. See [`packages/core/clusius_core/provision`](packages/core/clusius_core/provision).

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full system design and diagrams.

## Demo video

_Link pending._
