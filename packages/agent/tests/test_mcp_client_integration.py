"""Integration test: spawns the real docs MCP server as a subprocess over stdio and
calls it through MCPToolClient, to prove the client/server wiring actually works end
to end rather than only against mocks."""

from clusius_agent.mcp.client import MCPToolClient


async def test_search_docs_via_real_subprocess() -> None:
    client = MCPToolClient()

    results = await client.search_docs("KleidiAI matmul kernels on Arm", top_k=2)

    assert results
    assert results[0]["source"] == "kleidiai.md"
