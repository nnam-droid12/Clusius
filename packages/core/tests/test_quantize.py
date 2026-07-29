import subprocess
from pathlib import Path

import pytest
from clusius_core.migrate.quantize import (
    GGUFConvertConfig,
    GGUFQuantizeConfig,
    Int4QuantizeConfig,
    apply_int4_quantization,
    build_gguf_convert_command,
    build_gguf_quantize_command,
    convert_to_gguf,
    quantize_gguf,
)


def _ok_result(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")


def _fail_result(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="boom")


def test_build_gguf_quantize_command_basic() -> None:
    config = GGUFQuantizeConfig(
        llama_quantize_bin=Path("/app/llama-quantize"),
        input_gguf=Path("model-f16.gguf"),
        output_gguf=Path("model-q4.gguf"),
        quant_type="Q4_K_M",
    )

    cmd = build_gguf_quantize_command(config)

    assert cmd == ["/app/llama-quantize", "model-f16.gguf", "model-q4.gguf", "Q4_K_M"]


def test_build_gguf_quantize_command_with_threads() -> None:
    config = GGUFQuantizeConfig(
        llama_quantize_bin=Path("/app/llama-quantize"),
        input_gguf=Path("model-f16.gguf"),
        output_gguf=Path("model-q4.gguf"),
        quant_type="Q4_0",
        threads=8,
    )

    cmd = build_gguf_quantize_command(config)

    assert cmd[-1] == "8"


def test_quantize_gguf_raises_when_input_missing(tmp_path: Path) -> None:
    config = GGUFQuantizeConfig(
        llama_quantize_bin=Path("/app/llama-quantize"),
        input_gguf=tmp_path / "missing.gguf",
        output_gguf=tmp_path / "out.gguf",
        quant_type="Q4_K_M",
    )

    with pytest.raises(FileNotFoundError):
        quantize_gguf(config, runner=_ok_result)


def test_quantize_gguf_succeeds(tmp_path: Path) -> None:
    input_path = tmp_path / "model.gguf"
    input_path.write_bytes(b"fake gguf")
    config = GGUFQuantizeConfig(
        llama_quantize_bin=Path("/app/llama-quantize"),
        input_gguf=input_path,
        output_gguf=tmp_path / "out.gguf",
        quant_type="Q4_K_M",
    )

    result = quantize_gguf(config, runner=_ok_result)

    assert result == config.output_gguf


def test_quantize_gguf_raises_runtime_error_on_failure(tmp_path: Path) -> None:
    input_path = tmp_path / "model.gguf"
    input_path.write_bytes(b"fake gguf")
    config = GGUFQuantizeConfig(
        llama_quantize_bin=Path("/app/llama-quantize"),
        input_gguf=input_path,
        output_gguf=tmp_path / "out.gguf",
        quant_type="Q4_K_M",
    )

    with pytest.raises(RuntimeError, match="boom"):
        quantize_gguf(config, runner=_fail_result)


def test_build_gguf_convert_command() -> None:
    config = GGUFConvertConfig(
        convert_script=Path("/app/convert_hf_to_gguf.py"),
        model_dir=Path("/models/qwen2.5-7b"),
        output_gguf=Path("/out/model-f16.gguf"),
    )

    cmd = build_gguf_convert_command(config)

    assert cmd == [
        "python3",
        "/app/convert_hf_to_gguf.py",
        "/models/qwen2.5-7b",
        "--outfile",
        "/out/model-f16.gguf",
        "--outtype",
        "f16",
    ]


def test_convert_to_gguf_raises_when_model_dir_missing(tmp_path: Path) -> None:
    config = GGUFConvertConfig(
        convert_script=Path("/app/convert_hf_to_gguf.py"),
        model_dir=tmp_path / "missing-model",
        output_gguf=tmp_path / "out.gguf",
    )

    with pytest.raises(FileNotFoundError):
        convert_to_gguf(config, runner=_ok_result)


def test_apply_int4_quantization_raises_when_model_dir_missing(tmp_path: Path) -> None:
    config = Int4QuantizeConfig(model_dir=tmp_path / "missing", output_dir=tmp_path / "out")

    with pytest.raises(FileNotFoundError):
        apply_int4_quantization(config)
