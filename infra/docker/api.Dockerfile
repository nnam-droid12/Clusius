# syntax=docker/dockerfile:1
# clusius-api for Cloud Run: FastAPI app served by uvicorn, backed by an external
# Postgres (Neon) and Redis (Upstash) rather than sidecar containers.
FROM python:3.12-slim AS build

RUN pip install --no-cache-dir uv

WORKDIR /workspace
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/pyproject.toml
COPY packages/api/pyproject.toml packages/api/pyproject.toml
COPY packages/agent/pyproject.toml packages/agent/pyproject.toml

COPY packages/core packages/core
COPY packages/api packages/api

RUN uv sync --package clusius-api --no-dev --frozen

FROM python:3.12-slim AS runtime

WORKDIR /workspace
COPY --from=build /workspace/.venv /workspace/.venv
COPY --from=build /workspace/packages/core /workspace/packages/core
COPY --from=build /workspace/packages/api /workspace/packages/api
# clusius_core.pipeline needs this at runtime: it builds the backend image on the SSH
# targets from this Dockerfile (see LLAMACPP_DOCKERFILE in
# packages/core/clusius_core/pipeline.py).
COPY infra/docker/llamacpp-kleidi.Dockerfile infra/docker/llamacpp-kleidi.Dockerfile
# clusius_core.bench.schema_validate resolves this path relative to the repo root at
# runtime, to validate every BenchmarkResult against the open schema before it's used.
COPY bench/schema/result.schema.json bench/schema/result.schema.json

ENV PATH="/workspace/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8080
CMD ["uvicorn", "clusius_api.main:app", "--host", "0.0.0.0", "--port", "8080", "--app-dir", "packages/api"]
