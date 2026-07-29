# Benchmark methodology

_This document will be filled in with the exact hardware, model, load profile, and
methodology once the first real baseline + Arm run is captured. It is scaffolded now so
the structure is fixed before results land._

## Principles

- Every number in this repo is measured, never mocked or estimated.
- The x86 baseline and the Arm target run the same model task, the same prompt set, and
  the same load profile. Any unavoidable difference (thread count, instance class) is
  documented explicitly rather than hidden.
- Every result recorded in [`bench/results/`](bench/results/) carries hardware, instance
  type, image digest, model hash, and commit SHA so runs are traceable back to the exact
  code and artifacts that produced them.

## Hardware

| | Instance type | vCPUs | Arch |
|---|---|---|---|
| Baseline | TBD (e.g. `c4-standard-16`) | TBD | x86_64 |
| Target | TBD (e.g. `c4a-standard-16`) | TBD | aarch64 (Axion / Neoverse V2) |

## Workload

TBD — model, quantization-equivalent settings, prompt set, concurrency profile.

## Metrics captured

- Time to first token (TTFT)
- Inter-token latency
- End-to-end latency: p50 / p95 / p99
- Throughput: tokens/sec, requests/sec
- Cost per 1M tokens (derived from measured throughput and configured `$/hr`)
- Accuracy score against the task eval set

## Reproducing a run

See the "Setup / run / validate on Arm64" section of [`README.md`](README.md).
