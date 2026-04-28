"""
MemoryAgent — dedicated agent for cross-page memory operations.

Responsibilities:
  - Search memory for prior context on a topic
  - Write entity profiles and page summaries to memory
  - Return prior context so other agents can reason across pages

Used by the orchestrator BEFORE extraction to prime the extractor
with what ResearchMind already knows.
"""
import json
import re

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from llm import get_llm
from mcp_tools import get_tools

SYSTEM = """You are the Memory Agent for ResearchMind — a research assistant \
that builds knowledge across everything the user reads.

Your job is to manage the research memory store. You have access to memory \
tools for searching and writing notes.

When asked to RECALL:
1. Search memory using the provided query terms
2. Return a concise summary of what was found — entity names, key claims, \
   source URLs, any contradictions already noted
3. If nothing relevant is found, say so clearly

When asked to STORE:
1. Write a note for each entity with: name, type, description, source URL
2. Write a page summary note with: title, URL, key entities, main claims
3. Use consistent naming: "entity:{name}" for entities, page title for pages

Always be precise. The extractor agent depends on your recall to detect \
contradictions and patterns across sources."""


async def recall(query: str) -> str:
    """Search memory for prior context. Returns a plain-text summary."""
    tools = await get_tools(server="memory")
    if not tools:
        return ""

    llm = get_llm()
    agent = create_react_agent(llm, tools, prompt=SYSTEM)

    try:
        result = await agent.ainvoke({
            "messages": [HumanMessage(
                content=f"Search memory for: {query}\n"
                        f"Return a plain-text summary of what you find. "
                        f"Include entity names, key claims, and source URLs."
            )]
        })
        last = result["messages"][-1].content
        last = re.sub(r"<think>.*?</think>", "", last, flags=re.DOTALL).strip()
        return last[:1500]  # cap to avoid bloating extractor context
    except Exception as e:
        print(f"[MemoryAgent] Recall error: {e}")
        return ""


async def store(url: str, title: str, summary: str, entities: list[dict]) -> None:
    """Write page summary and entity profiles to memory."""
    tools = await get_tools(server="memory")
    if not tools:
        return

    llm = get_llm()
    agent = create_react_agent(llm, tools, prompt=SYSTEM)

    entity_list = "\n".join(
        f"- {e['name']} ({e.get('type','concept')}): {e.get('description','')}"
        for e in entities[:8]
    )

    try:
        await agent.ainvoke({
            "messages": [HumanMessage(
                content=(
                    f"Store the following research data in memory:\n\n"
                    f"Page title: {title}\n"
                    f"URL: {url}\n"
                    f"Summary: {summary}\n\n"
                    f"Entities:\n{entity_list}\n\n"
                    f"Write a note for the page (title='{title}') and "
                    f"individual notes for each entity (title='entity:{{name}}')."
                )
            )]
        })
    except Exception as e:
        print(f"[MemoryAgent] Store error: {e}")
