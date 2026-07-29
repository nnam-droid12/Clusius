from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from clusius_agent import serve
from clusius_agent.models import PipelineResult, StageTrace


def test_health() -> None:
    client = TestClient(serve.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_completions_returns_openai_shaped_response(monkeypatch) -> None:
    fake_result = PipelineResult(
        query="What is KleidiAI?",
        route="retrieve_docs",
        answer="KleidiAI is an Arm CPU kernel library.",
        retrieved=[],
        trace=[StageTrace(stage="route", duration_ms=1.0), StageTrace(stage="generate", duration_ms=5.0)],
    )
    monkeypatch.setattr(serve._pipeline, "run", AsyncMock(return_value=fake_result))

    client = TestClient(serve.app)
    response = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "What is KleidiAI?"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["choices"][0]["message"]["content"] == "KleidiAI is an Arm CPU kernel library."
    assert len(body["clusius_trace"]) == 2
