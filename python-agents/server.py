"""
ResearchMind Python Agent Server — http://localhost:3738

Routes:
  GET  /health     — status + current LLM config
  POST /config     — set LLM provider + API key at runtime
  POST /process    — run full agent pipeline on a page
  POST /synthesize — cross-session synthesis
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Literal, Optional

from agents.orchestrator import orchestrate
from agents.synthesis_agent import run_synthesis_agent
from llm import set_config, get_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[ResearchMind] 🚀 Agent server starting...")
    print(f"[ResearchMind] Default provider: {get_config()['provider']}")
    yield
    print("[ResearchMind] Shutting down.")


app = FastAPI(title="ResearchMind Agent Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class PagePayload(BaseModel):
    url: str
    title: str
    textContent: str
    headings: list[str] = []
    readDepth: float = 0.0


class BatchPayload(BaseModel):
    pages: list[PagePayload]


class ConfigPayload(BaseModel):
    provider: Literal["openai", "anthropic", "ollama"]
    api_key: Optional[str] = ""
    openai_model: Optional[str] = None
    anthropic_model: Optional[str] = None
    ollama_model: Optional[str] = None


@app.get("/health")
async def health():
    return {"ok": True, "agents": ["extractor", "memory", "graph", "synthesis"], **get_config()}


@app.post("/config")
async def config(payload: ConfigPayload):
    """Set LLM provider and API key at runtime — called from the extension popup."""
    try:
        set_config(
            provider=payload.provider,
            api_key=payload.api_key or "",
            openai_model=payload.openai_model,
            anthropic_model=payload.anthropic_model,
            ollama_model=payload.ollama_model,
        )
        return {"ok": True, **get_config()}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/process")
async def process_page(payload: PagePayload):
    """Process a single page through the agent pipeline."""
    try:
        result = await orchestrate(payload.model_dump())
        return result
    except Exception as e:
        print(f"[Agent Server] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/process-batch")
async def process_batch(payload: BatchPayload):
    """Process multiple pages concurrently — much faster than sequential."""
    try:
        tasks = [orchestrate(p.model_dump()) for p in payload.pages]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {
            "results": [r for r in results if not isinstance(r, Exception)],
            "errors": [str(r) for r in results if isinstance(r, Exception)]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/synthesize")
async def synthesize():
    """Cross-session synthesis across all saved research notes."""
    try:
        result = await run_synthesis_agent()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=3738, log_level="info")
    # NOTE: Run with python3.13, not python3 (3.14 has asyncio incompatibility with MCP)
    # python3.13 server.py
