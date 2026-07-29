# infra/docker

Base images built for `linux/arm64`:

- `llamacpp-kleidi.Dockerfile` — llama.cpp built from source with KleidiAI CPU kernels
  enabled, serving via `llama-server`.
- `vllm-acl.Dockerfile` — vLLM CPU build with oneDNN + Arm Compute Library kernels.
- `api.Dockerfile` / `web.Dockerfile` — application images used by `docker-compose.yml`.

Built multi-arch via `docker buildx build --platform linux/arm64` and validated in CI
(`.github/workflows/ci.yml`, `arm64-images` job).
