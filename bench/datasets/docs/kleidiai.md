# KleidiAI

KleidiAI is a set of open-source, performance-critical compute micro-kernels for AI
workloads on Arm CPUs, developed by Arm. It targets matrix multiplication routines used
by LLM inference (int4/int8 quantized matmul, dot-product kernels) and is tuned for
Armv8.2+ and Armv9 architectures such as Neoverse V2 (Google Axion / C4A).

Frameworks that link against KleidiAI's micro-kernels — including llama.cpp via its
Arm-optimized GEMM backends and XNNPACK — get the accelerated kernels automatically at
build time, with no changes required to model code or serving logic. On Neoverse V2,
KleidiAI's int4 kernels take advantage of the SDOT/UDOT and (where available) SME/SME2
instructions to raise prompt-processing and decode throughput over generic C++ matmul
implementations.

Because the uplift is a build-time/runtime kernel swap rather than a model change, the
correct way to measure its impact is a controlled A/B: the same GGUF model and
quantization, the same thread count and batch size, built once with KleidiAI kernels
linked in and once without, benchmarked on the same instance.
