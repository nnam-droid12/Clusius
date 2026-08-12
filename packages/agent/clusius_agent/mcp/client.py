"""Thin async client for calling Clusius's own MCP tool servers over stdio."""

from __future__ import annotations

import json
import sys
from typing import Any, cast

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import TextContent


async def _call_tool(module: str, tool_name: str, arguments: dict[str, Any]) -> Any:
    params = StdioServerParameters(command=sys.executable, args=["-m", module])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments)
            if result.is_error:
                raise RuntimeError(
                    f"MCP tool {tool_name!r} in {module!r} returned an error: {result.content}"
                )
            if result.structured_content is not None:
                # Non-object return types (e.g. a bare list) are wrapped by the SDK
                # as {"result": <value>} to satisfy the tool output JSON schema.
                if set(result.structured_content.keys()) == {"result"}:
                    return result.structured_content["result"]
                return result.structured_content
            (content,) = result.content
            if not isinstance(content, TextContent):
                raise RuntimeError(
                    f"MCP tool {tool_name!r} in {module!r} returned non-text content: "
                    f"{type(content).__name__}"
                )
            return json.loads(content.text)


class MCPToolClient:
    """Calls the docs and web-search MCP servers as short-lived stdio subprocesses."""

    def __init__(
        self,
        docs_module: str = "clusius_agent.mcp.docs_server",
        search_module: str = "clusius_agent.mcp.search_server",
    ) -> None:
        self.docs_module = docs_module
        self.search_module = search_module

    async def search_docs(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            await _call_tool(self.docs_module, "search_docs", {"query": query, "top_k": top_k}),
        )

    async def web_search(self, query: str, max_results: int = 5) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            await _call_tool(
                self.search_module, "web_search", {"query": query, "max_results": max_results}
            ),
        )
