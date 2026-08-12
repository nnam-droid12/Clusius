"""Validates a `BenchmarkResult` against the open schema at
`bench/schema/result.schema.json`, so the two never silently drift apart."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema

from clusius_core.models import BenchmarkResult

_REPO_ROOT = Path(__file__).resolve().parents[4]
_SCHEMA_PATH = _REPO_ROOT / "bench" / "schema" / "result.schema.json"


@lru_cache(maxsize=1)
def _load_schema() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return result


def validate_result(result: BenchmarkResult) -> None:
    jsonschema.validate(instance=result.to_schema_dict(), schema=_load_schema())
