# GGUF quantization

GGUF is the model container format used by llama.cpp. `llama-quantize` converts a
full-precision (fp16/bf16) checkpoint into a quantized GGUF file using one of several
quant types, trading model size and throughput against accuracy:

- `Q8_0` — near-lossless 8-bit quantization; largest of the quantized options, smallest
  accuracy loss versus fp16.
- `Q4_K_M` — 4-bit k-quant with mixed precision on more sensitive tensors; a common
  default balance of size, speed, and accuracy.
- `Q4_0` — plain 4-bit quantization; smaller and faster than `Q4_K_M` but with a larger
  accuracy gap on most tasks.

Lower-bit quant types shrink the weight matrices that dominate matmul time during
decode, which is why they raise tokens/sec on CPU backends — but each step down should
be re-validated against an accuracy floor rather than assumed safe, since the accuracy
cost varies by model family and task.
