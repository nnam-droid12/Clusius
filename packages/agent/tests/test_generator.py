from clusius_agent.generator import generate
from clusius_agent.models import RetrievedChunk
from clusius_agent.settings import AgentSettings

from tests.conftest import make_fake_openai_client


async def test_generate_returns_model_answer() -> None:
    client = make_fake_openai_client("KleidiAI accelerates matmul via Arm CPU micro-kernels.")
    settings = AgentSettings()

    answer = await generate("What is KleidiAI?", [], settings, client=client)

    assert answer == "KleidiAI accelerates matmul via Arm CPU micro-kernels."


async def test_generate_with_retrieved_context() -> None:
    client = make_fake_openai_client("Answer grounded in context.")
    settings = AgentSettings()
    retrieved = [
        RetrievedChunk(source="kleidiai.md", text="KleidiAI is a kernel library.", score=0.9)
    ]

    answer = await generate("What is KleidiAI?", retrieved, settings, client=client)

    assert answer == "Answer grounded in context."
