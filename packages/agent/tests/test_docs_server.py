from pathlib import Path
from typing import cast

from clusius_agent.mcp.docs_server import DocIndex

DOCS_PATH = Path(__file__).resolve().parents[3] / "bench" / "datasets" / "docs"


def test_search_ranks_relevant_doc_first() -> None:
    index = DocIndex(DOCS_PATH)

    results = index.search("KleidiAI matmul kernels on Neoverse V2", top_k=2)

    assert results
    assert results[0]["source"] == "kleidiai.md"
    assert cast(float, results[0]["score"]) > 0


def test_search_returns_nothing_for_unrelated_query() -> None:
    index = DocIndex(DOCS_PATH)

    results = index.search("zzz nonexistent term qqqqq", top_k=3)

    assert results == []


def test_search_respects_top_k() -> None:
    index = DocIndex(DOCS_PATH)

    results = index.search("Arm CPU quantization throughput", top_k=1)

    assert len(results) <= 1
