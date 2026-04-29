"""
ExtractorAgent — RAG-augmented ReAct agent.

Pipeline per page:
  1. RAG recall   — vector similarity search for prior context
  2. LLM extract  — entities, relationships, insights (informed by retrieved context)
  3. MCP persist  — write structured note to filesystem MCP
"""
import json
import re
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from llm import get_llm
from mcp_tools import get_tools, tool_names
from rag import retriever

RESEARCH_DIR = str(Path.home() / "ResearchMind")

# System prompt for the ReAct agent (filesystem tools only — RAG is handled before)
SYSTEM = """You are ResearchMind — an agentic research assistant that builds a \
connected knowledge graph across everything the user reads.

You have access to filesystem tools (read, write files).

━━━ YOUR TASK ━━━
You will receive:
  - A web page (URL, title, content)
  - PRIOR CONTEXT: semantically similar content retrieved from the research \
    knowledge base (RAG retrieval). This is what ResearchMind already knows.

Use the prior context to:
  - Detect CONTRADICTIONS: does this page conflict with something already stored?
  - Detect PATTERNS: does the same entity/claim appear across multiple sources?
  - Identify GAPS: what is referenced here but not yet in the knowledge base?
  - Mark DISCOVERIES: what is genuinely new?

━━━ STEP 1: PERSIST ━━━
Write a structured research note to the filesystem:

# {title}
URL: {url}
Summary: {2-3 sentences}

## Entities
- **{name}** ({type}): {description}

## Relationships
- {from} → {to}: {label} (confidence: {0.0-1.0})

## Insights
- [{type}]: {text — reference prior context sources by name when relevant}

## Prior Context Used
{summarize what the RAG retrieval returned, or "First page on this topic"}

━━━ FINAL RESPONSE ━━━
After writing the note, respond with ONLY valid JSON:
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
Contradictions must name the conflicting source. Patterns must name 2+ sources."""


async def run_extractor(url: str, title: str, text: str, headings: list[str]) -> dict:
    # ── Step 1: RAG recall ────────────────────────────────────────────────────
    query = f"{title} {' '.join(headings[:4])}"
    prior_context = await retriever.recall(query, k=5)

    if prior_context:
        print(f"[Extractor] RAG: retrieved prior context ({len(prior_context)} chars)")
    else:
        print("[Extractor] RAG: no prior context — first page on this topic")

    # ── Step 2: Build augmented prompt ────────────────────────────────────────
    page_input = _build_prompt(url, title, text, headings, prior_context)

    # ── Step 3: ReAct agent with filesystem MCP tools ─────────────────────────
    fs_tools = await get_tools(server="filesystem")

    if fs_tools:
        print(f"[Extractor] Tools: {', '.join(tool_names(fs_tools))}")
        llm = get_llm()
        agent = create_react_agent(llm, fs_tools, prompt=SYSTEM)
        try:
            result = await agent.ainvoke({"messages": [HumanMessage(content=page_input)]})
            last = result["messages"][-1].content
            extraction = _parse_json(last, title)
            extraction["prior_context_used"] = bool(prior_context)
            return extraction
        except Exception as e:
            print(f"[Extractor] Agent error: {e} — falling back to direct LLM")

    # ── Fallback: direct LLM call (no filesystem tools) ───────────────────────
    return await _direct_extract(page_input, title, bool(prior_context))


def _build_prompt(
    url: str,
    title: str,
    text: str,
    headings: list[str],
    prior_context: str,
) -> str:
    parts = [
        f"URL: {url}",
        f"Title: {title}",
        f"Headings: {' | '.join(headings[:8])}",
        "",
        "Content:",
        text[:5000],
    ]
    if prior_context:
        parts += [
            "",
            "━━━ PRIOR CONTEXT (RAG retrieval — what ResearchMind already knows) ━━━",
            prior_context,
            "━━━ END PRIOR CONTEXT ━━━",
        ]
    else:
        parts += ["", "PRIOR CONTEXT: None — this is the first page on this topic."]
    return "\n".join(parts)


async def _direct_extract(prompt: str, title: str, has_prior: bool) -> dict:
    """Direct LLM call when filesystem MCP is unavailable."""
    DIRECT_SYSTEM = (
        "You are a research analyst. Extract structured knowledge from the page below.\n"
        "If PRIOR CONTEXT is provided, use it to detect contradictions and patterns.\n"
        "Respond ONLY with valid JSON:\n"
        '{"summary":"...","entities":[{"name":"...","type":"person|concept|claim|'
        'study|organization|date|place","description":"..."}],'
        '"relationships":[{"from":"...","to":"...","label":"...","confidence":0.8}],'
        '"insights":[{"type":"discovery|contradiction|pattern|gap","text":"..."}],'
        '"prior_context_used":false}\n'
        "Max: 8 entities, 6 relationships, 4 insights."
    )
    llm = get_llm()
    response = await llm.ainvoke([
        SystemMessage(content=DIRECT_SYSTEM),
        HumanMessage(content=prompt),
    ])
    result = _parse_json(response.content, title)
    result["prior_context_used"] = has_prior
    return result


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
