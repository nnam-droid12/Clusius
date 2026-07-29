"""Answer synthesis via the larger generator model."""

from __future__ import annotations

from openai import AsyncOpenAI

from clusius_agent.models import RetrievedChunk
from clusius_agent.settings import AgentSettings

SYSTEM_PROMPT = """You are a research assistant. Answer the user's question concisely \
and accurately. If context passages are provided, ground your answer in them and note \
when the context doesn't fully answer the question rather than guessing."""


def _build_user_message(query: str, retrieved: list[RetrievedChunk]) -> str:
    if not retrieved:
        return query
    context = "\n\n".join(f"[{chunk.source}]\n{chunk.text}" for chunk in retrieved)
    return f"Context:\n{context}\n\nQuestion: {query}"


async def generate(
    query: str,
    retrieved: list[RetrievedChunk],
    settings: AgentSettings,
    client: AsyncOpenAI | None = None,
) -> str:
    owns_client = client is None
    active_client = client or AsyncOpenAI(
        base_url=settings.generator_base_url, api_key="not-needed", timeout=settings.request_timeout_s
    )
    try:
        response = await active_client.chat.completions.create(
            model=settings.generator_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_message(query, retrieved)},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content or ""
    finally:
        if owns_client:
            await active_client.close()
