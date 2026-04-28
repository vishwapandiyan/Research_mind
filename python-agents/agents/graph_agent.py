"""
GraphAgent — cross-page relationship and contradiction analysis.

Uses memory tools to look up existing entity profiles and detect:
  - Contradictions between new claims and stored knowledge
  - Patterns emerging across multiple sources
  - Gaps: referenced concepts not yet in memory
  - New relationships to add to the knowledge graph

Called by the orchestrator after extraction, enriches the reading
with deeper cross-page insights before it's saved to storage.
"""
import json
import re

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from llm import get_llm
from mcp_tools import get_tools

SYSTEM = """You are the Graph Agent for ResearchMind — responsible for \
maintaining a connected knowledge graph across all research sessions.

You have access to memory tools. Use them to:
1. Look up each key entity to see if it already exists in memory
2. Compare new claims against stored knowledge to find contradictions
3. Identify patterns — the same entity or claim appearing across sources
4. Flag gaps — entities referenced but not yet in memory

For each entity you look up:
- If found: does the new information confirm, contradict, or extend it?
- If not found: it's a discovery — note it as new

Be specific in your analysis:
- Contradictions must quote the conflicting claims and name both sources
- Patterns must name at least 2 sources where the entity/claim appears
- Gaps must describe what is unknown and why it matters

After your tool calls, respond with ONLY valid JSON:
{
  "enriched_insights": [
    {"type": "contradiction|pattern|gap|discovery",
     "text": "specific, grounded insight with source references"}
  ],
  "new_relationships": [
    {"from": "entity name", "to": "entity name",
     "label": "relationship type", "confidence": 0.0}
  ]
}"""


async def run_graph_agent(
    entities: list[dict],
    relationships: list[dict],
    url: str
) -> dict:
    """
    Enriches extraction results with cross-page graph analysis.
    Returns additional insights and relationships.
    """
    tools = await get_tools(server="memory")

    if not tools:
        # No memory available — return empty enrichment
        return {"enriched_insights": [], "new_relationships": []}

    llm = get_llm()
    agent = create_react_agent(llm, tools, prompt=SYSTEM)

    entity_summary = "\n".join(
        f"- {e['name']} ({e.get('type','concept')}): {e.get('description','')}"
        for e in entities[:10]
    )
    rel_summary = "\n".join(
        f"- {r.get('from','')} → {r.get('to','')}: {r.get('label','')}"
        for r in relationships[:8]
    )

    try:
        result = await agent.ainvoke({
            "messages": [HumanMessage(
                content=(
                    f"New page processed: {url}\n\n"
                    f"Entities extracted:\n{entity_summary}\n\n"
                    f"Relationships extracted:\n{rel_summary}\n\n"
                    f"Search memory for each key entity. Identify contradictions, "
                    f"patterns, gaps, and new relationships. "
                    f"Respond with JSON as instructed."
                )
            )]
        })
        last = result["messages"][-1].content
        last = re.sub(r"<think>.*?</think>", "", last, flags=re.DOTALL).strip()
        raw = re.sub(r"^```json\n?", "", last).rstrip("`").strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{[\s\S]*\}", raw)
            if match:
                return json.loads(match.group())
    except Exception as e:
        print(f"[GraphAgent] Error: {e}")

    return {"enriched_insights": [], "new_relationships": []}
