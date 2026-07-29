# syntax=docker/dockerfile:1
# vLLM CPU backend for linux/arm64. vLLM's own build (cmake/cpu_extension.cmake)
# auto-fetches and builds oneDNN with Arm Compute Library (ACL) as its GEMM backend
# whenever CMAKE_SYSTEM_PROCESSOR is aarch64 — no extra flags needed, unlike KleidiAI's
# opt-in flag in llama.cpp. This replicates the arm64 path of vLLM's own
# docker/Dockerfile.cpu (pinned commit below) via a shallow git fetch, since our build
# context is the Clusius repo rather than a vLLM checkout, plus adds llmcompressor for
# INT4 weight quantization.
ARG UBUNTU_VERSION=22.04
ARG VLLM_COMMIT=a0c092ee72c0dcefbb3b3e74f97ac62d842e5f4b
ARG PYTHON_VERSION=3.12

FROM docker.io/ubuntu:${UBUNTU_VERSION} AS vllm-src
ARG VLLM_COMMIT
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /vllm-workspace
# Retry a few times — this fetch has been observed to fail transiently under
# QEMU-emulated cross-arch builds (TLS stream errors on long-lived connections).
RUN git init -q \
    && git remote add origin https://github.com/vllm-project/vllm.git \
    && for i in 1 2 3 4 5; do \
        git fetch --depth 1 origin ${VLLM_COMMIT} && break; \
        echo "fetch attempt $i failed, retrying..." && sleep 5; \
    done \
    && git checkout -q FETCH_HEAD

# --- Rust frontend (vllm-rs), built separately per upstream's own Dockerfile so the
# main build stage doesn't need the Rust toolchain or protoc. ---
FROM docker.io/ubuntu:${UBUNTU_VERSION} AS rust-build
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl git build-essential unzip python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
COPY --from=vllm-src /vllm-workspace/tools/install_protoc.sh /tmp/install_protoc.sh
RUN /tmp/install_protoc.sh && rm /tmp/install_protoc.sh
COPY --from=vllm-src /vllm-workspace/requirements/build/rust.txt requirements/build/rust.txt
RUN python3 -m pip install --no-cache-dir -r requirements/build/rust.txt
COPY --from=vllm-src /vllm-workspace/rust rust
COPY --from=vllm-src /vllm-workspace/rust-toolchain.toml rust-toolchain.toml
COPY --from=vllm-src /vllm-workspace/tools/build_rust.py tools/build_rust.py
COPY --from=vllm-src /vllm-workspace/build_rust.sh build_rust.sh
ENV CARGO_BUILD_JOBS=4
RUN bash build_rust.sh

# --- CPU base: build deps + Python venv, arm64 only ---
FROM docker.io/ubuntu:${UBUNTU_VERSION} AS base
ARG PYTHON_VERSION
WORKDIR /vllm-workspace
RUN apt-get update -y \
    && apt-get install -y --no-install-recommends sudo ccache git curl wget ca-certificates \
        zlib1g-dev gcc-12 g++-12 libtcmalloc-minimal4 libnuma-dev ffmpeg libsm6 libxext6 \
        libgl1 jq lsof make xz-utils \
    && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-12 10 \
        --slave /usr/bin/g++ g++ /usr/bin/g++-12 \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*
ENV CC=/usr/bin/gcc-12 CXX=/usr/bin/g++-12
ENV PATH="/root/.local/bin:$PATH"
ENV VIRTUAL_ENV="/opt/venv"
RUN uv venv --python ${PYTHON_VERSION} --seed ${VIRTUAL_ENV}
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV UV_HTTP_TIMEOUT=500 UV_INDEX_STRATEGY="unsafe-best-match" UV_LINK_MODE="copy"
COPY --from=vllm-src /vllm-workspace/requirements/common.txt requirements/common.txt
COPY --from=vllm-src /vllm-workspace/requirements/cpu.txt requirements/cpu.txt
RUN uv pip install --upgrade pip && uv pip install -r requirements/cpu.txt --torch-backend cpu
ENV LD_PRELOAD="/usr/lib/aarch64-linux-gnu/libtcmalloc_minimal.so.4"
RUN echo 'ulimit -c 0' >> ~/.bashrc

# --- Build the vLLM CPU wheel (this is where oneDNN+ACL get fetched and built,
# gated on CMAKE_SYSTEM_PROCESSOR == aarch64 inside cmake/cpu_extension.cmake) ---
FROM base AS vllm-build
WORKDIR /vllm-workspace
COPY --from=vllm-src /vllm-workspace/requirements/build/cpu.txt requirements/build/cpu.txt
RUN uv pip install -r requirements/build/cpu.txt --torch-backend cpu
COPY --from=vllm-src /vllm-workspace .
COPY --from=rust-build /workspace/vllm/vllm-rs vllm/vllm-rs
COPY --from=rust-build /workspace/vllm/_rust_*.so vllm/
RUN VLLM_TARGET_DEVICE=cpu python3 setup.py bdist_wheel --dist-dir=dist --py-limited-api=cp38

# --- Runtime image ---
FROM base AS runtime
WORKDIR /vllm-workspace
RUN --mount=type=bind,from=vllm-build,src=/vllm-workspace/dist,target=dist \
    uv pip install "$(realpath dist/*.whl)"
RUN uv pip install llmcompressor
COPY --from=vllm-src /vllm-workspace/examples examples

LABEL org.opencontainers.image.title="vLLM CPU (Arm64, oneDNN+ACL)"
LABEL org.opencontainers.image.source="https://github.com/vllm-project/vllm"

EXPOSE 8000
ENTRYPOINT ["vllm", "serve"]
