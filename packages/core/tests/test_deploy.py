from __future__ import annotations

import httpx
import pytest
from clusius_core.migrate.deploy import (
    build_backend_image,
    ensure_docker_installed,
    start_llamacpp_server,
    start_vllm_server,
    stop_server,
    wait_for_health,
)
from clusius_core.migrate.ssh_runner import CommandResult
from clusius_core.tune.search_space import TrialConfig


class FakeRunner:
    """Stands in for TargetRunner: records every command, lets a test script canned
    results for specific commands (matched by substring)."""

    def __init__(self, scripted: dict[str, CommandResult] | None = None) -> None:
        self.commands: list[str] = []
        self.puts: list[tuple[str, str]] = []
        self._scripted = scripted or {}

    def run(self, command: str, raise_on_failure: bool = True) -> CommandResult:
        self.commands.append(command)
        for substring, result in self._scripted.items():
            if substring in command:
                if raise_on_failure and not result.ok:
                    raise RuntimeError(f"scripted failure for {command!r}")
                return result
        return CommandResult(command=command, exit_code=0, stdout="", stderr="")

    def put(self, local_path: str, remote_path: str) -> None:
        self.puts.append((local_path, remote_path))


def _trial_config(**overrides) -> TrialConfig:
    defaults = dict(
        backend="llamacpp",
        quant="Q4_K_M",
        threads=4,
        core_pinning=True,
        batch_size=8,
        kv_cache_precision="int8",
        context_length=4096,
    )
    defaults.update(overrides)
    return TrialConfig(**defaults)


def test_ensure_docker_installed_skips_when_present() -> None:
    runner = FakeRunner(scripted={"command -v docker": CommandResult("", 0, "/usr/bin/docker", "")})

    ensure_docker_installed(runner)  # type: ignore[arg-type]

    assert not any("get.docker.com" in c for c in runner.commands)


def test_ensure_docker_installed_installs_when_missing() -> None:
    runner = FakeRunner(scripted={"command -v docker": CommandResult("", 1, "", "not found")})

    ensure_docker_installed(runner)  # type: ignore[arg-type]

    assert any("get.docker.com" in c for c in runner.commands)


def test_build_backend_image_puts_dockerfile_and_builds_with_args() -> None:
    runner = FakeRunner()

    build_backend_image(
        runner,  # type: ignore[arg-type]
        dockerfile_local_path="infra/docker/llamacpp-kleidi.Dockerfile",
        tag="clusius-llamacpp:latest",
        build_args={"ENABLE_KLEIDIAI": "OFF"},
    )

    assert runner.puts == [
        ("infra/docker/llamacpp-kleidi.Dockerfile", "/tmp/clusius-build/Dockerfile")
    ]
    build_cmd = next(c for c in runner.commands if "docker build" in c)
    assert "--build-arg ENABLE_KLEIDIAI=OFF" in build_cmd
    assert "-t clusius-llamacpp:latest" in build_cmd


def test_stop_server_does_not_raise_when_container_absent() -> None:
    runner = FakeRunner(scripted={"docker rm -f": CommandResult("", 1, "", "no such container")})

    stop_server(runner)  # type: ignore[arg-type]

    assert any("docker rm -f clusius-server" in c for c in runner.commands)


def test_start_llamacpp_server_builds_expected_command() -> None:
    runner = FakeRunner()
    config = _trial_config(threads=4, batch_size=8, kv_cache_precision="int8", context_length=4096)

    start_llamacpp_server(runner, "clusius-llamacpp:latest", "/models/qwen.gguf", config, port=8080)  # type: ignore[arg-type]

    run_cmd = runner.commands[-1]
    assert "--cpuset-cpus=0-3" in run_cmd
    assert "-p 8080:8080" in run_cmd
    assert "-v /models/qwen.gguf:/model.gguf:ro" in run_cmd
    assert "--threads 4" in run_cmd
    assert "--ctx-size 4096" in run_cmd
    assert "--cache-type-k q8_0" in run_cmd
    assert "--batch-size 8" in run_cmd


def test_start_llamacpp_server_omits_cpuset_when_core_pinning_disabled() -> None:
    runner = FakeRunner()
    config = _trial_config(core_pinning=False)

    start_llamacpp_server(runner, "clusius-llamacpp:latest", "/models/qwen.gguf", config)  # type: ignore[arg-type]

    assert "--cpuset-cpus" not in runner.commands[-1]


def test_start_vllm_server_builds_expected_command() -> None:
    runner = FakeRunner()
    config = _trial_config(backend="vllm", quant="int4", threads=8, kv_cache_precision="fp16")

    start_vllm_server(runner, "clusius-vllm:latest", "Qwen/Qwen2.5-7B-Instruct", config, port=8000)  # type: ignore[arg-type]

    run_cmd = runner.commands[-1]
    assert "--cpuset-cpus=0-7" in run_cmd
    assert "-p 8000:8000" in run_cmd
    assert "Qwen/Qwen2.5-7B-Instruct" in run_cmd
    assert "--kv-cache-dtype auto" in run_cmd


async def test_wait_for_health_returns_when_healthy(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        return real_client(transport=transport)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)

    await wait_for_health("http://target:8080", timeout_s=5.0, poll_interval_s=0.01)


async def test_wait_for_health_times_out_when_never_healthy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def fake_client(*args, **kwargs):
        return real_client(transport=transport)

    monkeypatch.setattr(httpx, "AsyncClient", fake_client)

    with pytest.raises(TimeoutError):
        await wait_for_health("http://target:8080", timeout_s=0.05, poll_interval_s=0.01)
