from clusius_agent.router import classify
from clusius_agent.settings import AgentSettings

from tests.conftest import make_fake_openai_client, router_decision_json


async def test_classify_parses_direct_route() -> None:
    client = make_fake_openai_client(router_decision_json("direct"))
    settings = AgentSettings()

    decision = await classify("What is 2 + 2?", settings, client=client)

    assert decision.route == "direct"


async def test_classify_parses_retrieve_docs_route() -> None:
    client = make_fake_openai_client(
        router_decision_json("retrieve_docs", "matches local KleidiAI docs")
    )
    settings = AgentSettings()

    decision = await classify(
        "How does KleidiAI accelerate matmul on Arm?", settings, client=client
    )

    assert decision.route == "retrieve_docs"
    assert "KleidiAI" in decision.reasoning
