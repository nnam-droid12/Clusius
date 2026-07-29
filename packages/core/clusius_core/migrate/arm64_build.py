"""Builds the `docker buildx build --platform linux/arm64 ...` command for one of
Clusius's two backend Dockerfiles. Kept as a pure command builder (plus an injectable
runner) so it's unit-testable without Docker installed."""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Backend = Literal["llamacpp", "vllm"]

_DOCKERFILES: dict[Backend, str] = {
    "llamacpp": "infra/docker/llamacpp-kleidi.Dockerfile",
    "vllm": "infra/docker/vllm-acl.Dockerfile",
}

Runner = Callable[[list[str]], subprocess.CompletedProcess]


def _default_runner(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=False)


@dataclass
class Arm64BuildConfig:
    backend: Backend
    tag: str
    context: Path = Path(".")
    build_args: dict[str, str] = field(default_factory=dict)
    push: bool = False
    platform: str = "linux/arm64"


def build_command(config: Arm64BuildConfig) -> list[str]:
    dockerfile = _DOCKERFILES[config.backend]
    cmd = [
        "docker",
        "buildx",
        "build",
        "--platform",
        config.platform,
        "-f",
        dockerfile,
        "-t",
        config.tag,
    ]
    for key, value in config.build_args.items():
        cmd.extend(["--build-arg", f"{key}={value}"])
    cmd.append("--push" if config.push else "--load")
    cmd.append(str(config.context))
    return cmd


@dataclass
class BuildResult:
    tag: str
    image_digest: str | None
    stdout: str
    stderr: str


def build_arm64_image(config: Arm64BuildConfig, runner: Runner = _default_runner) -> BuildResult:
    result = runner(build_command(config))
    if result.returncode != 0:
        raise RuntimeError(
            f"arm64 build failed for backend {config.backend!r} "
            f"(exit {result.returncode}): {result.stderr}"
        )
    return BuildResult(
        tag=config.tag,
        image_digest=_extract_digest(result.stderr),
        stdout=result.stdout,
        stderr=result.stderr,
    )


def _extract_digest(build_output: str) -> str | None:
    for line in build_output.splitlines():
        line = line.strip()
        if line.startswith("sha256:"):
            return line
    return None
