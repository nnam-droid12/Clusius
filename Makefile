.PHONY: setup dev test lint typecheck fmt demo demo-replay db-upgrade clean

setup:
	uv sync --all-packages
	cd packages/web && npm install

dev:
	docker compose up -d postgres redis
	uv run --package clusius-api uvicorn clusius_api.main:app --reload --port 8000 &
	cd packages/web && npm run dev

test:
	uv run pytest packages/core/tests packages/api/tests packages/agent/tests
	cd packages/web && npm run test

lint:
	uv run ruff check .
	cd packages/web && npm run lint

typecheck:
	uv run mypy packages/core packages/api packages/agent
	cd packages/web && npm run typecheck

fmt:
	uv run ruff format .
	cd packages/web && npm run format

demo:
	uv run python -m clusius_core.cli run --config configs/demo.yaml

db-upgrade:
	uv run --package clusius-api alembic -c packages/api/alembic.ini upgrade head

# Zero-cost, zero-cloud-credential way to see the full live dashboard experience
# (stage timeline, trials landing on the Pareto chart, generated report) using the
# real, committed evidence in bench/results/ instead of a live C4A + x86 pair. Real
# numbers, replayed at a live pace — see the README's "Setup Instructions" section.
# Requires `make dev` (or at least `docker compose up -d postgres redis`) running.
demo-replay:
	uv run --package clusius-api alembic -c packages/api/alembic.ini upgrade head
	uv run --package clusius-api python -m clusius_api.scripts.demo_replay

clean:
	docker compose down -v
	find . -name "__pycache__" -type d -exec rm -rf {} +
