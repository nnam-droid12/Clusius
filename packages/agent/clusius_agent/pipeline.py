"""route -> (optional retrieve) -> generate, with a per-stage latency trace.

The trace is what lets Clusius attribute cost/latency to each model stage separately
(route on a small model, generate on a large one) rather than treating the agent as one
opaque call.
"""

from __future__ import annotations

import time

from clusius_agent import generator, router
from clusius_agent.mcp.client import MCPToolClient
from clusius_agent.models import PipelineResult, RetrievedChunk, StageTrace
from clusius_agent.settings import AgentSettings


class Pipeline:
    def __init__(
        self, settings: AgentSettings | None = None, mcp_client: MCPToolClient | None = None
    ) -> None:
        self.settings = settings or AgentSettings()
        self.mcp_client = mcp_client or MCPToolClient()

    async def run(self, query: str) -> PipelineResult:
        trace: list[StageTrace] = []

        start = time.perf_counter()
        decision = await router.classify(query, self.settings)
        trace.append(
            StageTrace(
                stage="route",
                duration_ms=(time.perf_counter() - start) * 1000,
                metadata={"route": decision.route, "reasoning": decision.reasoning},
            )
        )

        retrieved: list[RetrievedChunk] = []
        if decision.route == "retrieve_docs":
            start = time.perf_counter()
            hits = await self.mcp_client.search_docs(query, top_k=self.settings.docs_top_k)
            retrieved = [RetrievedChunk.model_validate(hit) for hit in hits]
            trace.append(
                StageTrace(
                    stage="retrieve_docs",
                    duration_ms=(time.perf_counter() - start) * 1000,
                    metadata={"hits": len(retrieved)},
                )
            )
        elif decision.route == "web_search":
            start = time.perf_counter()
            hits = await self.mcp_client.web_search(
                query, max_results=self.settings.web_search_max_results
            )
            retrieved = [
                RetrievedChunk(source=hit["url"], text=hit["snippet"], score=1.0)
                for hit in hits
                if hit.get("url")
            ]
            trace.append(
                StageTrace(
                    stage="web_search",
                    duration_ms=(time.perf_counter() - start) * 1000,
                    metadata={"hits": len(retrieved)},
                )
            )

        start = time.perf_counter()
        answer = await generator.generate(query, retrieved, self.settings)
        trace.append(
            StageTrace(
                stage="generate", duration_ms=(time.perf_counter() - start) * 1000, metadata={}
            )
        )

        return PipelineResult(
            query=query,
            route=decision.route,
            answer=answer,
            retrieved=retrieved,
            trace=trace,
        )
