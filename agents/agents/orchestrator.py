"""
OrchestratorAgent — drives the full multi-agent pipeline per page.

Pipeline:
  1. ExtractorAgent  — ReAct agent: recalls memory → extracts → writes note → stores entities
  2. GraphAgent      — ReAct agent: cross-references entities against memory,
                       enriches insights with contradictions/patterns/gaps
  3. MemoryAgent     — stores final enriched result for future pages to recall

Concurrency: asyncio.Semaphore(3) — max 3 pages processed simultaneously.
"""
import asyncio
import uuid
from datetime import datetime

from agents.extractor import run_extractor
from agents.graph_agent import run_graph_agent
from agents.memory_agent import store as memory_store

_semaphore = asyncio.Semaphore(3)


async def orchestrate(payload: dict) -> dict:
    async with _semaphore:
        return await _process(payload)


async def _process(payload: dict) -> dict:
    url = payload["url"]
    title = payload["title"]
    text = payload["textContent"]
    headings = payload.get("headings", [])
    read_depth = payload.get("readDepth", 0)
    domain = url.split("/")[2] if "//" in url else url.split("/")[0]

    print(f"\n[Orchestrator] ━━━ Processing: {title[:60]} ━━━")

    # ── Stage 1: Extract ──────────────────────────────────────────────────────
    # ReAct agent: searches memory → extracts → writes filesystem note → stores entities
    print("[Orchestrator] → ExtractorAgent (memory recall + extraction + persist)")
    extraction = await run_extractor(url, title, text, headings)

    entities = extraction.get("entities", [])
    relationships = extraction.get("relationships", [])
    insights = extraction.get("insights", [])
    summary = extraction.get("summary", title)
    used_prior = extraction.get("prior_context_used", False)

    print(f"[Orchestrator]   ✓ {len(entities)} entities, "
          f"{len(relationships)} relationships, {len(insights)} insights"
          f"{' [cross-page context used]' if used_prior else ''}")

    # ── Stage 2: Graph enrichment ─────────────────────────────────────────────
    # ReAct agent: looks up entities in memory, finds contradictions/patterns/gaps
    print("[Orchestrator] → GraphAgent (cross-page enrichment)")
    enrichment = await run_graph_agent(entities, relationships, url)

    extra_insights = enrichment.get("enriched_insights", [])
    extra_relationships = enrichment.get("new_relationships", [])

    if extra_insights:
        insights = insights + extra_insights
        print(f"[Orchestrator]   ✓ +{len(extra_insights)} enriched insights")
    if extra_relationships:
        relationships = relationships + extra_relationships
        print(f"[Orchestrator]   ✓ +{len(extra_relationships)} inferred relationships")

    # ── Stage 3: Memory store (fire-and-forget) ───────────────────────────────
    # Stores enriched result so future pages can recall it
    asyncio.create_task(
        _safe_memory_store(url, title, summary, entities)
    )

    print(f"[Orchestrator] ✅ Done — {len(entities)} entities, {len(insights)} insights total\n")

    # ── Build reading object ──────────────────────────────────────────────────
    return {
        "id": str(uuid.uuid4()),
        "url": url,
        "title": title,
        "domain": domain,
        "readAt": datetime.now().isoformat(),
        "textContent": "",  # stripped — not stored in chrome.storage
        "headings": headings,
        "summary": summary,
        "entities": [
            {
                "id": str(uuid.uuid4()),
                "name": e["name"],
                "type": e.get("type", "concept"),
                "description": e.get("description", ""),
                "firstSeenAt": url,
                "seenOnPages": [url],
                "relationships": [
                    r for r in relationships
                    if r.get("from") == e["name"] or r.get("to") == e["name"]
                ]
            }
            for e in entities
        ],
        "insights": [
            {
                "id": str(uuid.uuid4()),
                "type": ins.get("type", "discovery"),
                "text": ins.get("text", ""),
                "sourcePages": [url],
                "relatedEntities": [e["name"] for e in entities[:5]],
                "createdAt": datetime.now().isoformat()
            }
            for ins in insights
        ],
        "readDepth": read_depth
    }


async def _safe_memory_store(url: str, title: str, summary: str, entities: list) -> None:
    """Fire-and-forget memory write — errors are swallowed so they don't block the pipeline."""
    try:
        await asyncio.wait_for(
            memory_store(url, title, summary, entities),
            timeout=10.0
        )
    except Exception as e:
        print(f"[Orchestrator] Memory store skipped: {e}")
