"""
MCP Tools — filesystem MCP server only.

Memory/recall is now handled by the RAG vector store (rag.py / ChromaDB).
The filesystem MCP is used by ExtractorAgent (write notes) and
SynthesisAgent (read notes for cross-session synthesis).

  filesystem → http://localhost:8766/mcp
"""
import os
from pathlib import Path
from langchain_mcp_adapters.client import MultiServerMCPClient

RESEARCH_DIR = str(Path.home() / "ResearchMind")
os.makedirs(RESEARCH_DIR, exist_ok=True)

MCP_SERVERS = {
    "filesystem": {
        "url": "http://localhost:8766/mcp",
        "transport": "streamable_http",
    },
}

_cache: dict[str, list] = {}


async def get_tools(server: str | None = None) -> list:
    """Returns LangChain-compatible filesystem tools. Cached after first call."""
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
        print(f"[MCP] ✅ {len(tools)} filesystem tools: {', '.join(tool_names(tools))}")
        return tools
    except Exception as e:
        print(f"[MCP] ⚠️  Filesystem MCP unavailable: {e}")
        _cache[cache_key] = []
        return []


def tool_names(tools: list) -> list[str]:
    return [getattr(t, "name", str(t)) for t in tools]


def invalidate_cache() -> None:
    _cache.clear()
