"""Thin, testable wrappers around the two backends' quantization tools: llama.cpp's
`llama-quantize` (GGUF) and llmcompressor's INT4 weight-only recipe (vLLM).

Kept as pure command/recipe builders plus an injectable runner so the wrapper logic
(argument construction, error surfacing) is unit-testable without the actual binaries
or model weights present.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

GGUFQuantType = Literal["Q8_0", "Q4_K_M", "Q4_0", "Q4_K_S", "Q5_K_M", "Q6_K"]

Runner = Callable[[list[str]], subprocess.CompletedProcess]


def _default_runner(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


@dataclass
class GGUFQuantizeConfig:
    llama_quantize_bin: Path
    input_gguf: Path
    output_gguf: Path
    quant_type: GGUFQuantType
    threads: int | None = None


def build_gguf_quantize_command(config: GGUFQuantizeConfig) -> list[str]:
    # .as_posix() rather than str(): these binaries always run inside a Linux
    # container or over SSH on a Linux target, regardless of the host OS this
    # orchestration code happens to run on.
    cmd = [
        config.llama_quantize_bin.as_posix(),
        config.input_gguf.as_posix(),
        config.output_gguf.as_posix(),
        config.quant_type,
    ]
    if config.threads is not None:
        cmd.append(str(config.threads))
    return cmd


def quantize_gguf(config: GGUFQuantizeConfig, runner: Runner = _default_runner) -> Path:
    if not config.input_gguf.exists():
        raise FileNotFoundError(f"input GGUF not found: {config.input_gguf}")

    result = runner(build_gguf_quantize_command(config))
    if result.returncode != 0:
        raise RuntimeError(
            f"llama-quantize failed (exit {result.returncode}) converting "
            f"{config.input_gguf} to {config.quant_type}: {result.stderr}"
        )
    return config.output_gguf


@dataclass
class GGUFConvertConfig:
    convert_script: Path
    model_dir: Path
    output_gguf: Path
    outtype: str = "f16"


def build_gguf_convert_command(config: GGUFConvertConfig) -> list[str]:
    return [
        "python3",
        config.convert_script.as_posix(),
        config.model_dir.as_posix(),
        "--outfile",
        config.output_gguf.as_posix(),
        "--outtype",
        config.outtype,
    ]


def convert_to_gguf(config: GGUFConvertConfig, runner: Runner = _default_runner) -> Path:
    if not config.model_dir.exists():
        raise FileNotFoundError(f"model directory not found: {config.model_dir}")

    result = runner(build_gguf_convert_command(config))
    if result.returncode != 0:
        raise RuntimeError(
            f"convert_hf_to_gguf failed (exit {result.returncode}) for "
            f"{config.model_dir}: {result.stderr}"
        )
    return config.output_gguf


@dataclass
class Int4QuantizeConfig:
    model_dir: Path
    output_dir: Path
    scheme: str = "W4A16"


def apply_int4_quantization(config: Int4QuantizeConfig) -> Path:
    """Applies an llmcompressor INT4 weight-only recipe to a HF model directory,
    saving the quantized model to `output_dir` for vLLM to serve.

    `llmcompressor` is an optional dependency of the migration engine (only needed on
    hosts that actually run the vLLM quantization step, e.g. the build/CI host — not
    every environment importing `clusius_core`), so it's imported lazily here.
    """
    if not config.model_dir.exists():
        raise FileNotFoundError(f"model directory not found: {config.model_dir}")

    from llmcompressor import oneshot
    from llmcompressor.modifiers.quantization import QuantizationModifier

    recipe = QuantizationModifier(targets="Linear", scheme=config.scheme, ignore=["lm_head"])
    oneshot(
        model=str(config.model_dir),
        recipe=recipe,
        output_dir=str(config.output_dir),
    )
    return config.output_dir
