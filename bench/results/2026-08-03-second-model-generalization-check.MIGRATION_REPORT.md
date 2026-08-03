# Migration Report: second-model-generalization-check

Generated 2026-08-03T03:37:58.772975+00:00 · commit `unknown`

## Baseline

| | |
|---|---|
| Model | `TinyLlama/TinyLlama-1.1B-Chat-v1.0` |
| Instance | `c4-standard-2` (x86_64) |
| Threads | 1 |
| Backend | llamacpp (Q8_0) |
| Throughput | 13.0 tok/s |
| p95 latency | 36047 ms |
| Cost / 1M tokens | $2.0723 |

## Changes made

No x86-only blockers were found in the workload's build configuration.

Optimizations applied on the Arm64 build:

- Q8_0 quantization
- 1 threads
- KleidiAI CPU kernels linked (Arm build)
- core pinning enabled
- KV cache precision: int8

## Backend selection

Selected llama.cpp+KleidiAI: at your measured concurrency of 2, it delivered 34.9 tok/s at 100.0% accuracy (floor 50.0%) and 14559ms p95 latency (SLA 60000ms).

## Chosen configuration

| | |
|---|---|
| Instance | `c4a-standard-2` (aarch64) |
| Backend | llamacpp |
| Quantization | Q8_0 |
| Threads | 1 |
| Core pinning | True |
| Batch size | 4 |
| KV cache precision | int8 |
| Context length | 2048 |

## Results

| Metric | x86 baseline | Arm winner | Delta |
|---|---|---|---|
| Throughput (tok/s) | 13.0 | 34.9 | +168.6% |
| p95 latency (ms) | 36047 | 14559 | -59.6% |
| Cost / 1M tokens | $2.0723 | $0.7149 | -65.5% |
| Accuracy | 100.0% | 100.0% | +0.0pp |


## Why this configuration

- **Accuracy**: 100.0%, against a floor of 50.0%.
- **Latency**: 14559ms p95, against an SLA of 60000ms.
- **Cost**: -65.5% vs. the x86 baseline at 4.0 trials searched.

Full trial history, raw per-request data, and the machine-readable result are available in `result.json` alongside this report.