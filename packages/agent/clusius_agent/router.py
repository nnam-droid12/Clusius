"""Query routing via the small router model.

The router decides, for a given query, whether to answer directly, retrieve from the
local document store, or issue a web search — before the (larger, more expensive)
generator model ever runs. This is the stage Clusius optimizes independently from
generation: it is latency-sensitive and low-context, so it is the natural candidate for
the most aggressive quantization in the auto-tune search.
"""

from __future__ import annotations

import json

from openai import AsyncOpenAI

from clusius_agent.models import RouterDecision
from clusius_agent.settings import AgentSettings

SYSTEM_PROMPT = """You are a routing component in a research agent. Given a user \
query, decide how it should be answered. Respond with ONLY a JSON object of the form \
{"route": "direct" | "retrieve_docs" | "web_search", "reasoning": "<one sentence>"}.

- "direct": the query is general knowledge, conversational, or answerable without \
looking anything up.
- "retrieve_docs": the query is about topics likely covered in the agent's local \
document store (Arm CPU optimization, KleidiAI, GGUF quantization, vLLM, Axion/C4A).
- "web_search": the query needs current or external information not likely to be in \
the local document store.
"""


async def classify(query: str, settings: AgentSettings, client: AsyncOpenAI | None = None) -> RouterDecision:
    owns_client = client is None
    active_client = client or AsyncOpenAI(
        base_url=settings.router_base_url, api_key="not-needed", timeout=settings.request_timeout_s
    )
    try:
        response = await active_client.chat.completions.create(
            model=settings.router_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": query},
            ],
            temperature=0,
            max_tokens=200,
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        return RouterDecision.model_validate(data)
    finally:
        if owns_client:
            await active_client.close()
