import subprocess
from pathlib import Path

import pytest
from clusius_core.migrate.arm64_build import Arm64BuildConfig, build_arm64_image, build_command


def _ok(stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], returncode=0, stdout="", stderr=stderr)


def _fail() -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(
        [], returncode=1, stdout="", stderr="build failed: missing base image"
    )


def test_build_command_for_llamacpp() -> None:
    config = Arm64BuildConfig(backend="llamacpp", tag="clusius/llamacpp-kleidi:latest")

    cmd = build_command(config)

    assert cmd == [
        "docker",
        "buildx",
        "build",
        "--platform",
        "linux/arm64",
        "-f",
        "infra/docker/llamacpp-kleidi.Dockerfile",
        "-t",
        "clusius/llamacpp-kleidi:latest",
        "--load",
        ".",
    ]


def test_build_command_for_vllm_with_push_and_args() -> None:
    config = Arm64BuildConfig(
        backend="vllm",
        tag="clusius/vllm-acl:latest",
        push=True,
        build_args={"PYTHON_VERSION": "3.12"},
    )

    cmd = build_command(config)

    assert "infra/docker/vllm-acl.Dockerfile" in cmd
    assert "--build-arg" in cmd
    assert "PYTHON_VERSION=3.12" in cmd
    assert "--push" in cmd
    assert "--load" not in cmd


def test_build_arm64_image_success() -> None:
    config = Arm64BuildConfig(backend="llamacpp", tag="clusius/llamacpp-kleidi:test")

    result = build_arm64_image(config, runner=lambda cmd: _ok(stderr="  sha256:abc123def456\n"))

    assert result.tag == "clusius/llamacpp-kleidi:test"
    assert result.image_digest == "sha256:abc123def456"


def test_build_arm64_image_raises_on_failure() -> None:
    config = Arm64BuildConfig(backend="vllm", tag="clusius/vllm-acl:test")

    with pytest.raises(RuntimeError, match="missing base image"):
        build_arm64_image(config, runner=lambda cmd: _fail())


def test_build_command_uses_custom_context(tmp_path: Path) -> None:
    config = Arm64BuildConfig(backend="llamacpp", tag="t", context=tmp_path)

    cmd = build_command(config)

    assert cmd[-1] == str(tmp_path)
