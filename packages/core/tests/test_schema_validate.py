from typing import Any

import pytest
from clusius_core.bench.schema_validate import validate_result
from clusius_core.models import BenchmarkResult, LatencyPercentiles, ThroughputMetrics, utcnow
from jsonschema import ValidationError
from pydantic import ValidationError as PydanticValidationError


def _valid_result(**overrides: Any) -> BenchmarkResult:
    defaults: dict[str, Any] = dict(
        run_id="test-run-1",
        timestamp=utcnow(),
        commit_sha="abc123",
        model="qwen2.5-7b-instruct",
        model_hash="sha256:deadbeef",
        backend="llamacpp",
        quant="Q4_K_M",
        instance_type="c4a-standard-16",
        arch="aarch64",
        price_per_hour=0.5,
        threads=16,
        concurrency=4,
        throughput=ThroughputMetrics(tokens_per_second=50.0, requests_per_second=1.0),
        latency_ms=LatencyPercentiles(ttft_p50=100.0, p50=500.0, p95=900.0, p99=1200.0),
        cost_per_1m_tokens=2.5,
        accuracy_score=0.95,
    )
    defaults.update(overrides)
    return BenchmarkResult(**defaults)


def test_valid_result_passes_schema() -> None:
    validate_result(_valid_result())


def test_schema_rejects_bad_arch_value() -> None:
    result = _valid_result()
    dumped = result.to_schema_dict()
    dumped["arch"] = "risc-v"

    import jsonschema
    from clusius_core.bench.schema_validate import _load_schema

    with pytest.raises(ValidationError):
        jsonschema.validate(instance=dumped, schema=_load_schema())


def test_schema_rejects_accuracy_above_one() -> None:
    with pytest.raises(PydanticValidationError):
        _valid_result(accuracy_score=1.5)
