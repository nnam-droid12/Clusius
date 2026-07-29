# syntax=docker/dockerfile:1
# llama.cpp built for linux/arm64 with KleidiAI CPU kernels linked in, plus the Python
# GGUF conversion/quantization tooling. Pinned against a known-good llama.cpp commit so
# the KleidiAI CMake flag below (`GGML_CPU_KLEIDIAI`, see ggml/src/ggml-cpu/CMakeLists.txt)
# is verified rather than guessed — re-check that flag name if bumping the pin.
ARG UBUNTU_VERSION=24.04
ARG LLAMA_CPP_COMMIT=caa596ab3f0f8768ee326d6e3d5d39782194676c

FROM docker.io/ubuntu:${UBUNTU_VERSION} AS build
ARG LLAMA_CPP_COMMIT

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
# Shallow-fetch just the pinned commit rather than a full clone: cloning the entire
# history under emulation is slow enough to hit connection resets on some hosts.
# Retry a few times — the fetch has been observed to fail transiently under
# QEMU-emulated cross-arch builds (TLS stream errors on long-lived connections).
RUN git init -q \
    && git remote add origin https://github.com/ggml-org/llama.cpp.git \
    && for i in 1 2 3 4 5; do \
        git fetch --depth 1 origin ${LLAMA_CPP_COMMIT} && break; \
        echo "fetch attempt $i failed, retrying..." && sleep 5; \
    done \
    && git checkout -q FETCH_HEAD

# GGML_CPU_KLEIDIAI links Arm's KleidiAI micro-kernels into the CPU backend (see
# infra/docker/README.md and bench/datasets/docs/kleidiai.md for what this buys us).
# GGML_NATIVE tunes for the build host's CPU (Neoverse V2 on C4A); LLAMA_BUILD_UI=OFF
# skips the npm/web-ui build stage since Clusius drives llama-server via its HTTP API.
RUN cmake -S . -B build \
        -DCMAKE_BUILD_TYPE=Release \
        -DGGML_NATIVE=ON \
        -DGGML_CPU_KLEIDIAI=ON \
        -DLLAMA_BUILD_TESTS=OFF \
        -DLLAMA_BUILD_EXAMPLES=OFF \
        -DLLAMA_BUILD_UI=OFF \
    && cmake --build build --config Release -j "$(nproc)" --target llama-server llama-quantize llama-cli

FROM docker.io/ubuntu:${UBUNTU_VERSION} AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 curl python3 python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=build /src/build/bin/llama-server /src/build/bin/llama-quantize /src/build/bin/llama-cli /app/
COPY --from=build /src/convert_hf_to_gguf.py /app/
COPY --from=build /src/gguf-py /app/gguf-py
COPY --from=build /src/requirements/requirements-convert_hf_to_gguf.txt /app/requirements-convert.txt

RUN pip install --break-system-packages --no-cache-dir -r /app/requirements-convert.txt

ENV LLAMA_ARG_HOST=0.0.0.0
EXPOSE 8080
HEALTHCHECK CMD ["curl", "-f", "http://localhost:8080/health"]

ENTRYPOINT ["/app/llama-server"]
