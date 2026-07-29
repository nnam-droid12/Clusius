.PHONY: setup dev test lint typecheck fmt demo clean

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

clean:
	docker compose down -v
	find . -name "__pycache__" -type d -exec rm -rf {} +
