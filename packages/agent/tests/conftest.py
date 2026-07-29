import json

import httpx
from openai import AsyncOpenAI


def make_fake_openai_client(content: str) -> AsyncOpenAI:
    """An AsyncOpenAI client wired to a mock transport that always returns `content`
    as the assistant message, so router/generator logic can be tested without a real
    inference server running."""

    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "id": "chatcmpl-test",
            "object": "chat.completion",
            "created": 0,
            "model": "test-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
        }
        return httpx.Response(200, json=body)

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport)
    return AsyncOpenAI(base_url="http://test/v1", api_key="not-needed", http_client=http_client)


def router_decision_json(route: str, reasoning: str = "test reasoning") -> str:
    return json.dumps({"route": route, "reasoning": reasoning})
