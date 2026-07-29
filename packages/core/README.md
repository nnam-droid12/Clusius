# clusius-core

The Clusius engine. Framework-agnostic Python package implementing the five pipeline
stages:

- `clusius_core/analyze` — workload introspection and migration planning.
- `clusius_core/migrate` — Arm64 rebuild, backend wiring, quantization.
- `clusius_core/tune` — Optuna multi-objective search and backend selection.
- `clusius_core/bench` — load generator, metrics, and cost model.
- `clusius_core/provision` — GCP C4A provisioning (target-mode and provisioned-mode).
- `clusius_core/report` — `MIGRATION_REPORT.md` and `result.json` generation.

`clusius-api` depends on this package and drives it as background jobs; it has no
dependency of its own on FastAPI, SQLAlchemy, or the web stack, so it can be used
standalone (e.g. from a CLI or notebook) to run a migration.
