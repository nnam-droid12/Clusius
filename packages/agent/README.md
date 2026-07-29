# clusius-agent

A multi-model RAG/research agent used as the showcase workload that Clusius migrates
and optimizes: a small router model, a larger generator model, and two MCP tool
servers (web search/retrieval and a document/vector store).

- `router.py` — classifies the query and decides retrieval vs. direct answer / tool use.
- `generator.py` — synthesizes the final answer.
- `mcp/` — MCP client and tool wiring.
- `pipeline.py` — route → (optional) retrieve → generate, with a per-stage trace so
  Clusius can optimize each stage independently.
- `serve.py` — OpenAI-compatible endpoint wrapper so the benchmark harness can drive it
  uniformly regardless of backend.

All models run locally on CPU (llama.cpp / vLLM) — no hosted LLM APIs.
