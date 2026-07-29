# clusius-api

FastAPI orchestration layer. Owns Postgres persistence (SQLAlchemy + Alembic) and drives
`clusius-core` pipeline runs as background jobs via an `arq`/Redis worker, streaming
stage progress to the dashboard over Server-Sent Events.

The web app talks only to this API — it never accesses the database directly.

## Surface

- `POST /runs` — launch a migration + optimization run.
- `GET /runs` — list runs.
- `GET /runs/{id}` — run detail.
- `GET /runs/{id}/events` — SSE stream of stage/trial progress.
- `GET /runs/{id}/report` — rendered `MIGRATION_REPORT.md`.
- `GET /runs/{id}/result.json` — schema-conformant result.
- `GET /results` — run history.

OpenAPI docs are auto-generated at `/docs`.
