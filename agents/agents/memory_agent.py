"""
MemoryAgent — RAG-backed cross-page memory.

Uses ChromaDB vector store (via rag.py) instead of basic-memory MCP.
Provides semantic recall with scored results and structured storage.

recall()  → vector similarity search → formatted context for LLM injection
store()   → chunk + embed + upsert into ChromaDB
"""
from rag import retriever


async def recall(query: str) -> str:
    """
    Semantic search over all stored research.
    Returns a formatted context block ready for LLM injection.

    Example:
        [1] From arxiv.org (2024-01-15) — "CRISPR Applications":
        CRISPR-Cas9 has been shown to achieve 94% efficiency...
        Relevance: 0.82
    """
    context = await retriever.recall(query, k=5)
    if context:
        print(f"[MemoryAgent] RAG recall: found relevant prior context")
    else:
        print(f"[MemoryAgent] RAG recall: no prior context found")
    return context


async def store(
    url: str,
    title: str,
    summary: str,
    entities: list[dict],
    full_text: str = "",
) -> None:
    """
    Chunk, embed, and store a page in the vector store.
    Stores page chunks, summary, and entity profiles separately
    so each can be retrieved independently.
    """
    n = await retriever.store(url, title, summary, entities, full_text)
    print(f"[MemoryAgent] Stored {n} vectors for: {title[:50]}")
