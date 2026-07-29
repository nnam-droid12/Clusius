# vLLM with oneDNN and Arm Compute Library

vLLM's CPU backend can be built against oneDNN and Arm Compute Library (ACL) to get
Arm-optimized matmul and attention kernels, and paired with INT4 weight quantization
(via `llmcompressor`) for further throughput gains on Arm servers.

The main advantage vLLM brings over a single-stream server like llama.cpp's
`llama-server` is continuous batching: incoming requests are dynamically batched at the
scheduler level, so at higher concurrency the CPU spends more of its time on efficient
batched matmuls instead of being latency-bound on a single stream. This tends to win on
aggregate tokens/sec under concurrent load, at some cost to single-request
time-to-first-token versus an unloaded llama.cpp server.

The practical implication for backend selection: workloads that are single-stream or
low-concurrency (an interactive chat session, a CLI tool) tend to favor llama.cpp's
lower per-request latency; workloads that serve many concurrent requests (an API
serving many users) tend to favor vLLM's batched throughput, provided the accuracy cost
of INT4 quantization stays within the target's accuracy floor.
