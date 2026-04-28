"""
MCP Tools — connects to locally running MCP servers via HTTP transport.

Servers are started by mcp-bridge/server.js (stdio) OR start_mcp_servers.py (HTTP).
This module connects to the HTTP endpoints.

  basic-memory  → http://localhost:8765/mcp
  filesystem    → http://localhost:8766/mcp
"""
import os
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient

RESEARCH_DIR = str(Path.home() / "ResearchMind")
os.makedirs(RESEARCH_DIR, exist_ok=True)

MCP_SERVERS = {
    "memory": {
        "url": "http://localhost:8765/mcp",
        "transport": "streamable_http",
    },
    "filesystem": {
        "url": "http://localhost:8766/mcp",
        "transport": "streamable_http",
    },
}

# Cache tools for the process lifetime — MCP connections are expensive
_cache: dict[str, list] = {}


async def get_tools(server: str | None = None) -> list:
    """
    Returns LangChain-compatible tools for the given MCP server (or all).
    Cached after first call.
    """
    cache_key = server or "__all__"
    if cache_key in _cache:
        return _cache[cache_key]

    servers = (
        {server: MCP_SERVERS[server]}
        if server and server in MCP_SERVERS
        else MCP_SERVERS
    )

    try:
        client = MultiServerMCPClient(servers)
        tools = await client.get_tools()
        _cache[cache_key] = tools
        print(f"[MCP] ✅ {len(tools)} tools loaded: {', '.join(tool_names(tools))}")
        return tools
    except Exception as e:
        print(f"[MCP] ⚠️  Could not connect ({cache_key}): {e}")
        print("[MCP]    → Ensure start_mcp_servers.py is running")
        _cache[cache_key] = []
        return []


def tool_names(tools: list) -> list[str]:
    """Extract tool names from a list of LangChain tools."""
    return [getattr(t, "name", str(t)) for t in tools]


def invalidate_cache() -> None:
    """Force re-connection on next get_tools() call."""
    _cache.clear()
