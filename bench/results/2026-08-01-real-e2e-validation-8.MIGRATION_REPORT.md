# Migration Report: real-e2e-validation-8

Generated 2026-08-01T15:29:05.300288+00:00 · commit `unknown`

## Baseline

| | |
|---|---|
| Model | `Qwen/Qwen2.5-0.5B-Instruct` |
| Instance | `c4-standard-2` (x86_64) |
| Threads | 2 |
| Backend | llamacpp (Q8_0) |
| Throughput | 33.9 tok/s |
| p95 latency | 22238 ms |
| Cost / 1M tokens | $0.7946 |

## Changes made

No x86-only blockers were found in the workload's build configuration.

Optimizations applied on the Arm64 build:

- Q8_0 quantization
- 2 threads
- KleidiAI CPU kernels linked (Arm build)
- core pinning enabled
- KV cache precision: int8

## Backend selection

Selected llama.cpp+KleidiAI: at your measured concurrency of 2, it delivered 91.7 tok/s at 100.0% accuracy (floor 50.0%) and 4470ms p95 latency (SLA 30000ms).

## Chosen configuration

| | |
|---|---|
| Instance | `c4a-standard-2` (aarch64) |
| Backend | llamacpp |
| Quantization | Q8_0 |
| Threads | 2 |
| Core pinning | True |
| Batch size | 4 |
| KV cache precision | int8 |
| Context length | 2048 |

## Results

| Metric | x86 baseline | Arm winner | Delta |
|---|---|---|---|
| Throughput (tok/s) | 33.9 | 91.7 | +170.7% |
| p95 latency (ms) | 22238 | 4470 | -79.9% |
| Cost / 1M tokens | $0.7946 | $0.2720 | -65.8% |
| Accuracy | 100.0% | 100.0% | +0.0pp |


## Why this configuration

- **Accuracy**: 100.0%, against a floor of 50.0%.
- **Latency**: 4470ms p95, against an SLA of 30000ms.
- **Cost**: -65.8% vs. the x86 baseline at 4.0 trials searched.

Full trial history, raw per-request data, and the machine-readable result are available in `result.json` alongside this report.