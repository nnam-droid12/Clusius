# Migration Report: real-e2e-validation-7

Generated 2026-07-31T07:03:46.725906+00:00 · commit `unknown`

## Baseline

| | |
|---|---|
| Model | `Qwen/Qwen2.5-0.5B-Instruct` |
| Instance | `c4-standard-2` (x86_64) |
| Threads | 2 |
| Backend | llamacpp (Q8_0) |
| Throughput | 29.2 tok/s |
| p95 latency | 30050 ms |
| Cost / 1M tokens | $0.0000 |

## Changes made

No x86-only blockers were found in the workload's build configuration.

Optimizations applied on the Arm64 build:

- Q8_0 quantization
- 2 threads
- KleidiAI CPU kernels linked (Arm build)
- KV cache precision: fp16

## Backend selection

Selected llama.cpp+KleidiAI: at your measured concurrency of 2, it delivered 98.8 tok/s at 100.0% accuracy (floor 50.0%) and 8397ms p95 latency (SLA 30000ms).

## Chosen configuration

| | |
|---|---|
| Instance | `c4a-standard-2` (aarch64) |
| Backend | llamacpp |
| Quantization | Q8_0 |
| Threads | 2 |
| Core pinning | False |
| Batch size | 4 |
| KV cache precision | fp16 |
| Context length | 2048 |

## Results

| Metric | x86 baseline | Arm winner | Delta |
|---|---|---|---|
| Throughput (tok/s) | 29.2 | 98.8 | +238.9% |
| p95 latency (ms) | 30050 | 8397 | -72.1% |
| Cost / 1M tokens | $0.0000 | $0.0000 | +0.0% |
| Accuracy | 100.0% | 100.0% | +0.0pp |


## Why this configuration

- **Accuracy**: 100.0%, against a floor of 50.0%.
- **Latency**: 8397ms p95, against an SLA of 30000ms.
- **Cost**: +0.0% vs. the x86 baseline at 4.0 trials searched.

Full trial history, raw per-request data, and the machine-readable result are available in `result.json` alongside this report.