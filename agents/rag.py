"""
RAG — Retrieval-Augmented Generation for ResearchMind.

Replaces basic-memory MCP with a proper vector store pipeline:
  - Embeddings via Ollama (nomic-embed-text) or OpenAI (text-embedding-3-small)
  - ChromaDB as the local persistent vector store
  - Chunked document storage with rich metadata
  - Scored similarity retrieval with source attribution

Usage:
    from rag import retriever

    # Store a page after extraction
    await retriever.store(url, title, summary, entities, full_text)

    # Retrieve prior context before extraction
    context = await retriever.recall(query, k=5)
    # → "From arxiv.org (2024-01-15): CRISPR-Cas9 was shown to..."
"""
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

# ChromaDB
import chromadb
from chromadb.config import Settings

# LangChain splitter + embeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CHROMA_DIR = str(Path.home() / "ResearchMind" / ".chroma")
COLLECTION_NAME = "researchmind"

# Chunk settings — tuned for research content
CHUNK_SIZE = 600
CHUNK_OVERLAP = 100
TOP_K = 5                    # chunks to retrieve per query
MIN_RELEVANCE_SCORE = 0.3    # discard chunks below this cosine similarity


# ── Embedding factory ─────────────────────────────────────────────────────────

def _get_embedding_fn():
    """
    Returns a ChromaDB-compatible embedding function.
    Uses Ollama nomic-embed-text by default (local, free).
    Falls back to OpenAI text-embedding-3-small if OPENAI_API_KEY is set
    and provider is openai.
    """
    provider = os.getenv("RESEARCHMIND_PROVIDER", "ollama")

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
        print("[RAG] Using OpenAI text-embedding-3-small")
        return OpenAIEmbeddingFunction(
            api_key=os.getenv("OPENAI_API_KEY"),
            model_name="text-embedding-3-small",
        )

    # Default: Ollama nomic-embed-text (768-dim, fast, local)
    from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
    print("[RAG] Using Ollama nomic-embed-text")
    return OllamaEmbeddingFunction(
        url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model_name="nomic-embed-text",
    )


# ── Vector store singleton ────────────────────────────────────────────────────

class VectorStore:
    """
    Persistent ChromaDB vector store for ResearchMind.

    Documents are chunked and stored with metadata:
      - url, title, domain, stored_at
      - chunk_index (position within the original document)
      - doc_type: "page" | "entity" | "summary"

    Retrieval returns scored chunks with source attribution,
    formatted as a plain-text context block ready for LLM injection.
    """

    def __init__(self) -> None:
        os.makedirs(CHROMA_DIR, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=CHROMA_DIR,
            settings=Settings(anonymized_telemetry=False),
        )
        self._embed_fn = _get_embedding_fn()
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        print(f"[RAG] Vector store ready — {self._collection.count()} chunks stored")

    # ── Store ─────────────────────────────────────────────────────────────────

    def store_page(
        self,
        url: str,
        title: str,
        summary: str,
        entities: list[dict],
        full_text: str,
    ) -> int:
        """
        Chunk and embed a page. Stores:
          - The full page text (chunked)
          - A summary document
          - Entity profiles (one doc per entity)

        Returns the number of chunks stored.
        """
        domain = _extract_domain(url)
        stored_at = datetime.utcnow().isoformat()
        docs: list[Document] = []

        # 1. Chunk the full page text
        if full_text.strip():
            chunks = self._splitter.split_text(full_text[:8000])
            for i, chunk in enumerate(chunks):
                docs.append(Document(
                    page_content=chunk,
                    metadata={
                        "url": url, "title": title, "domain": domain,
                        "stored_at": stored_at, "chunk_index": i,
                        "doc_type": "page",
                    }
                ))

        # 2. Summary as a single document
        if summary.strip():
            docs.append(Document(
                page_content=f"Summary of '{title}': {summary}",
                metadata={
                    "url": url, "title": title, "domain": domain,
                    "stored_at": stored_at, "chunk_index": 0,
                    "doc_type": "summary",
                }
            ))

        # 3. Entity profiles
        for entity in entities[:10]:
            name = entity.get("name", "")
            etype = entity.get("type", "concept")
            desc = entity.get("description", "")
            if not name:
                continue
            docs.append(Document(
                page_content=f"{name} ({etype}): {desc}. Source: {url}",
                metadata={
                    "url": url, "title": title, "domain": domain,
                    "stored_at": stored_at, "chunk_index": 0,
                    "doc_type": "entity", "entity_name": name,
                }
            ))

        if not docs:
            return 0

        # Deduplicate by content hash to avoid re-embedding on re-runs
        ids = [_doc_id(url, d.metadata["doc_type"], d.metadata["chunk_index"]) for d in docs]
        texts = [d.page_content for d in docs]
        metadatas = [d.metadata for d in docs]

        # upsert — safe to call multiple times for the same page
        self._collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
        print(f"[RAG] Stored {len(docs)} chunks for: {title[:50]}")
        return len(docs)

    # ── Recall ────────────────────────────────────────────────────────────────

    def recall(self, query: str, k: int = TOP_K) -> str:
        """
        Semantic search over all stored research.
        Returns a formatted context block for LLM injection.

        Example output:
            [1] From arxiv.org (2024-01-15) — "CRISPR Applications":
            CRISPR-Cas9 has been shown to achieve 94% efficiency in...
            Relevance: 0.82

            [2] From nature.com (2024-01-10) — "Gene Editing Review":
            ...
        """
        total = self._collection.count()
        if total == 0:
            return ""

        results = self._collection.query(
            query_texts=[query],
            n_results=min(k, total),
            include=["documents", "metadatas", "distances"],
        )

        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        if not docs:
            return ""

        lines = []
        for i, (doc, meta, dist) in enumerate(zip(docs, metas, distances), 1):
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity score 0–1
            similarity = max(0.0, 1.0 - dist / 2.0)
            if similarity < MIN_RELEVANCE_SCORE:
                continue

            domain = meta.get("domain", "unknown")
            title = meta.get("title", "Untitled")
            stored_at = meta.get("stored_at", "")[:10]  # date only
            doc_type = meta.get("doc_type", "page")

            label = f"[{i}] From {domain} ({stored_at}) — \"{title}\""
            if doc_type == "entity":
                label += f" [entity: {meta.get('entity_name', '')}]"

            lines.append(f"{label}:\n{doc.strip()}\nRelevance: {similarity:.2f}")

        if not lines:
            return ""

        return "\n\n".join(lines)

    def count(self) -> int:
        return self._collection.count()

    def clear(self) -> None:
        """Delete all stored vectors. Used for testing or reset."""
        self._client.delete_collection(COLLECTION_NAME)
        self._collection = self._client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
        print("[RAG] Vector store cleared")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_domain(url: str) -> str:
    try:
        return url.split("/")[2]
    except IndexError:
        return url


def _doc_id(url: str, doc_type: str, chunk_index: int) -> str:
    """Stable ID for upsert deduplication."""
    import hashlib
    key = f"{url}::{doc_type}::{chunk_index}"
    return hashlib.md5(key.encode()).hexdigest()


# ── Async wrappers ────────────────────────────────────────────────────────────
# ChromaDB is synchronous — run in thread pool to avoid blocking the event loop.

class AsyncRetriever:
    """Async wrapper around VectorStore for use in async agent code."""

    def __init__(self) -> None:
        self._store: Optional[VectorStore] = None

    def _get_store(self) -> VectorStore:
        if self._store is None:
            self._store = VectorStore()
        return self._store

    async def store(
        self,
        url: str,
        title: str,
        summary: str,
        entities: list[dict],
        full_text: str = "",
    ) -> int:
        return await asyncio.to_thread(
            self._get_store().store_page,
            url, title, summary, entities, full_text,
        )

    async def recall(self, query: str, k: int = TOP_K) -> str:
        return await asyncio.to_thread(
            self._get_store().recall, query, k
        )

    async def count(self) -> int:
        return await asyncio.to_thread(self._get_store().count)

    async def clear(self) -> None:
        await asyncio.to_thread(self._get_store().clear)


# Module-level singleton — import this everywhere
retriever = AsyncRetriever()
