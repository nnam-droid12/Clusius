"""OpenAI-compatible HTTP wrapper around the agent pipeline.

Exposes just enough of the Chat Completions surface for the benchmark harness
(`clusius_core.bench`) to drive the agent the same way it drives a raw llama.cpp/vLLM
endpoint, so the harness doesn't need an agent-specific code path.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from fastapi import FastAPI
from pydantic import BaseModel

from clusius_agent.pipeline import Pipeline
from clusius_agent.settings import AgentSettings

app = FastAPI(title="clusius-agent")
_pipeline = Pipeline()


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "clusius-agent"
    messages: list[ChatMessage]


class ChatChoice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str = "stop"


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    clusius_trace: list[dict[str, Any]] = []


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
    user_messages = [m.content for m in request.messages if m.role == "user"]
    query = user_messages[-1] if user_messages else ""

    result = await _pipeline.run(query)

    return ChatCompletionResponse(
        id=f"clusius-{uuid.uuid4().hex}",
        created=int(time.time()),
        model=request.model,
        choices=[ChatChoice(index=0, message=ChatMessage(role="assistant", content=result.answer))],
        clusius_trace=[stage.model_dump() for stage in result.trace],
    )


def main() -> None:
    import uvicorn

    settings = AgentSettings()
    uvicorn.run(app, host=settings.serve_host, port=settings.serve_port)


if __name__ == "__main__":
    main()
