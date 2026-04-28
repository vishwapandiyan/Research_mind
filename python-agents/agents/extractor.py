"""
ExtractorAgent — ReAct agent that uses MCP memory + filesystem tools
to build cross-page knowledge with full context awareness.

Tool call sequence per page:
  1. search_notes (memory)     — recall what we know about this topic
  2. LLM reasoning             — extract entities/relationships/insights
                                 informed by prior context
  3. write_file (filesystem)   — persist structured research note
  4. write_note (memory)       — store entity profiles for future recall
"""
import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from llm import get_llm
from mcp_tools import get_tools, tool_names

RESEARCH_DIR = str(Path.home() / "ResearchMind")

SYSTEM = """You are ResearchMind — an agentic research assistant that builds a \
connected knowledge graph across everything the user reads.

You have access to memory tools (search, write notes) and filesystem tools \
(read, write files). Use them in this exact sequence:

━━━ STEP 1: RECALL ━━━
Search memory for prior context. Call the memory search tool with the page \
title and 2-3 key terms from the content. This tells you what you already know \
about this topic across previous pages.

━━━ STEP 2: ANALYZE ━━━
With the page content AND prior context in mind, identify:
• Entities — people, concepts, claims, studies, organizations, dates, places
• Relationships — how entities connect (authored, contradicts, supports, \
  part_of, cites, challenges, extends)
• Insights — be specific and grounded:
  - DISCOVERY: genuinely new information not seen before
  - CONTRADICTION: name the specific conflicting claim and its source
  - PATTERN: must reference at least 2 sources by name
  - GAP: a concept referenced but not yet explored

━━━ STEP 3: PERSIST ━━━
Write a structured research note to the filesystem. Use this format:

# {title}
URL: {url}
Summary: {2-3 sentences}

## Entities
- **{name}** ({type}): {description}

## Relationships
- {from} → {to}: {label} (confidence: {0.0-1.0})

## Insights
- [{type}]: {text}

## Prior Context Used
{what memory search returned, or "First page on this topic"}

━━━ STEP 4: REMEMBER ━━━
For each key entity (max 5), write a short memory note so future pages can \
find it. Title format: "entity:{name}". Content: type, description, source URL.

━━━ FINAL RESPONSE ━━━
After all tool calls, respond with ONLY valid JSON — no markdown, no preamble:
{
  "summary": "2-3 sentence summary",
  "entities": [
    {"name": "...", "type": "person|concept|claim|study|organization|date|place",
     "description": "..."}
  ],
  "relationships": [
    {"from": "...", "to": "...", "label": "...", "confidence": 0.0}
  ],
  "insights": [
    {"type": "discovery|contradiction|pattern|gap", "text": "..."}
  ],
  "prior_context_used": true|false
}

Limits: 10 entities, 8 relationships, 4 insights.
Never skip Step 1 or Step 3. Always use tools."""


async def run_extractor(url: str, title: str, text: str, headings: list[str]) -> dict:
    tools = await get_tools()

    if not tools:
        print("[Extractor] ⚠️  No MCP tools — using fallback LLM call")
        return await _fallback_extract(url, title, text, headings)

    available = tool_names(tools)
    print(f"[Extractor] 🔧 Tools available: {', '.join(available)}")

    llm = get_llm()
    agent = create_react_agent(llm, tools, prompt=SYSTEM)

    page_input = (
        f"URL: {url}\n"
        f"Title: {title}\n"
        f"Headings: {' | '.join(headings[:8])}\n\n"
        f"Content:\n{text[:5000]}"
    )

    try:
        result = await agent.ainvoke({
            "messages": [HumanMessage(content=page_input)]
        })
        last = result["messages"][-1].content
        return _parse_json(last, title)
    except Exception as e:
        print(f"[Extractor] ❌ Agent error: {e} — falling back to bare LLM")
        return await _fallback_extract(url, title, text, headings)


def _parse_json(raw: str, title: str) -> dict:
    raw = re.sub(r"<think>[\s\S]*?</think>", "", raw).strip()
    raw = re.sub(r"^```json\n?", "", raw).rstrip("`").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return {"summary": title, "entities": [], "relationships": [], "insights": []}


async def _fallback_extract(url: str, title: str, text: str, headings: list[str]) -> dict:
    """Bare LLM call — used only when MCP servers are unreachable."""
    from langchain_core.messages import SystemMessage, HumanMessage

    FALLBACK = (
        "Extract structured knowledge from this web page.\n"
        "Respond ONLY with valid JSON:\n"
        '{"summary":"...","entities":[{"name":"...","type":"person|concept|claim|'
        'study|organization|date|place","description":"..."}],'
        '"relationships":[{"from":"...","to":"...","label":"...","confidence":0.8}],'
        '"insights":[{"type":"discovery|contradiction|pattern|gap","text":"..."}]}\n'
        "Max: 8 entities, 6 relationships, 3 insights."
    )
    llm = get_llm()
    prompt = (
        f"URL: {url}\nTitle: {title}\n"
        f"Headings: {' | '.join(headings[:8])}\n\nContent:\n{text[:4000]}"
    )
    response = await llm.ainvoke([
        SystemMessage(content=FALLBACK),
        HumanMessage(content=prompt)
    ])
    return _parse_json(response.content, title)
