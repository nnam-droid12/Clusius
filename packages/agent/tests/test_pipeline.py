import pytest
from clusius_agent import generator, router
from clusius_agent.models import RouterDecision
from clusius_agent.pipeline import Pipeline
from clusius_agent.settings import AgentSettings


class FakeMCPClient:
    def __init__(self) -> None:
        self.docs_calls: list[str] = []
        self.search_calls: list[str] = []

    async def search_docs(self, query: str, top_k: int = 3) -> list[dict]:
        self.docs_calls.append(query)
        return [{"source": "kleidiai.md", "text": "KleidiAI kernel details.", "score": 0.8}]

    async def web_search(self, query: str, max_results: int = 5) -> list[dict]:
        self.search_calls.append(query)
        return [{"title": "Result", "url": "https://example.com", "snippet": "snippet text"}]


@pytest.fixture
def pipeline(monkeypatch: pytest.MonkeyPatch) -> tuple[Pipeline, FakeMCPClient]:
    fake_mcp = FakeMCPClient()
    p = Pipeline(settings=AgentSettings(), mcp_client=fake_mcp)
    return p, fake_mcp


async def test_direct_route_skips_retrieval(
    monkeypatch: pytest.MonkeyPatch, pipeline: tuple
) -> None:
    p, fake_mcp = pipeline

    async def fake_classify(query, settings, client=None):
        return RouterDecision(route="direct", reasoning="general knowledge")

    async def fake_generate(query, retrieved, settings, client=None):
        return "42"

    monkeypatch.setattr(router, "classify", fake_classify)
    monkeypatch.setattr(generator, "generate", fake_generate)

    result = await p.run("What is 6 times 7?")

    assert result.route == "direct"
    assert result.answer == "42"
    assert result.retrieved == []
    assert fake_mcp.docs_calls == []
    assert [stage.stage for stage in result.trace] == ["route", "generate"]


async def test_retrieve_docs_route_calls_docs_search(
    monkeypatch: pytest.MonkeyPatch, pipeline: tuple
) -> None:
    p, fake_mcp = pipeline

    async def fake_classify(query, settings, client=None):
        return RouterDecision(route="retrieve_docs", reasoning="matches local docs")

    async def fake_generate(query, retrieved, settings, client=None):
        assert len(retrieved) == 1
        return "grounded answer"

    monkeypatch.setattr(router, "classify", fake_classify)
    monkeypatch.setattr(generator, "generate", fake_generate)

    result = await p.run("How does KleidiAI work?")

    assert result.route == "retrieve_docs"
    assert len(result.retrieved) == 1
    assert fake_mcp.docs_calls == ["How does KleidiAI work?"]
    assert [stage.stage for stage in result.trace] == ["route", "retrieve_docs", "generate"]


async def test_web_search_route_calls_web_search(
    monkeypatch: pytest.MonkeyPatch, pipeline: tuple
) -> None:
    p, fake_mcp = pipeline

    async def fake_classify(query, settings, client=None):
        return RouterDecision(route="web_search", reasoning="needs current info")

    async def fake_generate(query, retrieved, settings, client=None):
        return "web-grounded answer"

    monkeypatch.setattr(router, "classify", fake_classify)
    monkeypatch.setattr(generator, "generate", fake_generate)

    result = await p.run("What's the latest Arm Neoverse release?")

    assert result.route == "web_search"
    assert fake_mcp.search_calls == ["What's the latest Arm Neoverse release?"]
    assert result.retrieved[0].source == "https://example.com"
