"""MCP server exposing a `web_search` tool backed by DuckDuckGo's HTML search.

No API key required, which keeps the showcase agent's tool wiring free of external
credentials. Network failures are surfaced as an empty result list rather than raised,
so a flaky connection degrades the agent's retrieval quality instead of crashing it.
"""

from __future__ import annotations

from mcp.server import MCPServer

server = MCPServer("clusius-search")


@server.tool()
def web_search(query: str, max_results: int = 5) -> list[dict[str, str]]:
    """Search the web and return title/url/snippet for the top matching results."""
    from duckduckgo_search import DDGS

    try:
        with DDGS() as ddgs:
            hits = ddgs.text(query, max_results=max_results)
    except Exception:
        return []

    return [
        {
            "title": hit.get("title", ""),
            "url": hit.get("href", ""),
            "snippet": hit.get("body", ""),
        }
        for hit in hits
    ]


mcp = server

if __name__ == "__main__":
    mcp.run()
