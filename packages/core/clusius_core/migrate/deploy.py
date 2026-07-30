"""SSH-driven backend deployment: builds a backend's Docker image natively on the
target host — no cross-compilation/emulation needed, since target-mode SSHes directly
into the real architecture — then manages the serving container's lifecycle so the
tuner's trial loop can start/stop/reconfigure it between trials.
"""

from __future__ import annotations

import asyncio
import time

import httpx

from clusius_core.migrate.ssh_runner import TargetRunner
from clusius_core.tune.search_space import TrialConfig

CONTAINER_NAME = "clusius-server"
LLAMACPP_PORT = 8080
VLLM_PORT = 8000


def ensure_docker_installed(runner: TargetRunner) -> None:
    check = runner.run("command -v docker", raise_on_failure=False)
    if check.ok:
        return
    runner.run("curl -fsSL https://get.docker.com | sudo sh", raise_on_failure=True)


def build_backend_image(
    runner: TargetRunner,
    dockerfile_local_path: str,
    tag: str,
    build_args: dict[str, str] | None = None,
    remote_build_dir: str = "/tmp/clusius-build",
) -> None:
    runner.run(f"mkdir -p {remote_build_dir}")
    runner.put(dockerfile_local_path, f"{remote_build_dir}/Dockerfile")
    args = " ".join(f"--build-arg {k}={v}" for k, v in (build_args or {}).items())
    runner.run(
        f"cd {remote_build_dir} && sudo docker build {args} -t {tag} -f Dockerfile .",
        raise_on_failure=True,
    )


def stop_server(runner: TargetRunner) -> None:
    runner.run(f"sudo docker rm -f {CONTAINER_NAME}", raise_on_failure=False)


def _kv_cache_type(precision: str) -> str:
    return "q8_0" if precision == "int8" else "f16"


def start_llamacpp_server(
    runner: TargetRunner,
    image_tag: str,
    model_gguf_path: str,
    config: TrialConfig,
    port: int = LLAMACPP_PORT,
) -> None:
    stop_server(runner)
    cache_type = _kv_cache_type(config.kv_cache_precision)
    cpuset = f"0-{max(config.threads - 1, 0)}"
    cpuset_flag = f"--cpuset-cpus={cpuset}" if config.core_pinning else ""
    cmd = (
        f"sudo docker run -d --name {CONTAINER_NAME} --rm "
        f"{cpuset_flag} -p {port}:{LLAMACPP_PORT} "
        f"-v {model_gguf_path}:/model.gguf:ro "
        f"{image_tag} "
        f"-m /model.gguf --threads {config.threads} --ctx-size {config.context_length} "
        f"--cache-type-k {cache_type} --batch-size {config.batch_size} "
        f"--host 0.0.0.0 --port {LLAMACPP_PORT}"
    )
    runner.run(cmd, raise_on_failure=True)


def start_vllm_server(
    runner: TargetRunner,
    image_tag: str,
    model_ref: str,
    config: TrialConfig,
    port: int = VLLM_PORT,
) -> None:
    stop_server(runner)
    cpuset = f"0-{max(config.threads - 1, 0)}"
    cpuset_flag = f"--cpuset-cpus={cpuset}" if config.core_pinning else ""
    kv_dtype = "fp8" if config.kv_cache_precision == "int8" else "auto"
    cmd = (
        f"sudo docker run -d --name {CONTAINER_NAME} --rm "
        f"{cpuset_flag} -p {port}:{VLLM_PORT} "
        f"-e VLLM_CPU_OMP_THREADS_BIND={config.threads} "
        f"{image_tag} "
        f"{model_ref} --port {VLLM_PORT} --max-model-len {config.context_length} "
        f"--max-num-seqs {config.batch_size} --kv-cache-dtype {kv_dtype}"
    )
    runner.run(cmd, raise_on_failure=True)


def server_port(backend: str) -> int:
    return LLAMACPP_PORT if backend == "llamacpp" else VLLM_PORT


async def wait_for_health(
    base_url: str, timeout_s: float = 180.0, poll_interval_s: float = 2.0
) -> None:
    deadline = time.monotonic() + timeout_s
    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(f"{base_url}/health", timeout=5.0)
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"server at {base_url} did not become healthy within {timeout_s}s"
                )
            await asyncio.sleep(poll_interval_s)
