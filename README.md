<p align="center">
  <img src="assets/icon.png" width="80" alt="ResearchMind" />
</p>

<h1 align="center">ResearchMind</h1>

<p align="center">
  An always-on agentic research assistant that lives in your browser.<br/>
  It reads everything you browse, builds a connected knowledge graph across all your sources,<br/>
  and surfaces contradictions, patterns, and insights you would never catch manually.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/LangChain-ReAct_Agents-blue?style=flat-square" />
  <img src="https://img.shields.io/badge/MCP-basic--memory_%2B_filesystem-purple?style=flat-square" />
  <img src="https://img.shields.io/badge/RAG-semantic_recall-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/Guardrails-input_%2B_output-red?style=flat-square" />
  <img src="https://img.shields.io/badge/LLM-Ollama_%7C_GPT--4o_%7C_Claude-green?style=flat-square" />
  <img src="https://img.shields.io/badge/Chrome-Manifest_V3-yellow?style=flat-square" />
</p>

---

## The Problem

You read across dozens of tabs. Every time you close one, that context is gone.

- You read a study on Monday and a contradicting paper on Friday — you never notice they conflict
- You visit 10 pages on the same topic and still can't see the pattern
- Every research session starts from scratch — no memory of what you already know
- You manually copy notes, lose the thread between sources, and miss the connections that matter

**The browser has no memory. You do all the synthesis yourself.**

---

## The Solution

ResearchMind runs silently as you browse. It reads every page you visit, extracts structured knowledge, and connects it to everything you have read before — across sessions, across sites.

```
You browse normally.
ResearchMind builds the picture.
```

For every page you visit, a multi-agent pipeline:

1. **Recalls** what it already knows about this topic from memory (RAG)
2. **Extracts** entities, claims, and relationships — informed by prior context
3. **Cross-references** each entity against stored knowledge to find contradictions and patterns
4. **Validates** all inputs and outputs through guardrails before saving
5. **Persists** structured notes and entity profiles for future recall
6. **Updates** a live knowledge graph and insight feed in the dashboard

---

## How ResearchMind is Different

Most tools summarize pages. ResearchMind connects them.

| | ResearchMind | Notion AI | Readwise | Browser bookmarks |
|---|---|---|---|---|
| Reads pages automatically | ✅ | ❌ | ❌ | ❌ |
| Cross-page memory (RAG) | ✅ | ❌ | ❌ | ❌ |
| Detects contradictions | ✅ | ❌ | ❌ | ❌ |
| Knowledge graph visualization | ✅ | ❌ | ❌ | ❌ |
| Runs fully local | ✅ | ❌ | ❌ | ✅ |
| Multi-agent ReAct pipeline | ✅ | ❌ | ❌ | ❌ |
| MCP tool integration | ✅ | ❌ | ❌ | ❌ |
| Input + output guardrails | ✅ | ❌ | ❌ | ❌ |
| Structured observability | ✅ | ❌ | ❌ | ❌ |
| Works across sessions | ✅ | ✅ | ✅ | ✅ |

The key difference: every insight is grounded in **what you have already read**. Contradictions name the conflicting source. Patterns reference at least two sources by name. The agent knows what it knows before it reads anything new.

---

## What You Get

### Live Knowledge Graph
An interactive force-directed graph built with `react-force-graph-2d`. Every entity extracted from every page becomes a node. Every relationship becomes an edge.

- Nodes are **color-coded by type** — person (blue), concept (purple), claim (amber), study (green), organization (pink), place (cyan), date (gray)
- Node **size scales with how many pages** mention that entity — the more sources, the bigger the node
- **Click any node** to see its description, all pages that mention it, and all its relationships
- **Filter by entity type** to focus on people, concepts, claims, studies, or organizations
- Edges are labeled with the relationship type (authored, contradicts, supports, part\_of, cites, challenges)

### Insight Feed
A real-time stream of agent-generated insights, color-coded and filterable:

| Type | Color | Meaning |
|---|---|---|
| 🔍 Discovery | Blue | Genuinely new information not seen before |
| ⚡ Contradiction | Red | A claim that conflicts with something from a prior source |
| 🔗 Pattern | Purple | A theme or entity appearing across multiple sources |
| ❓ Gap | Amber | A concept referenced but not yet explored |

Each insight links back to its source pages.

### Source Feed
Chronological list of every page read. Each card shows the favicon, title, domain, agent-generated summary, and insight tags. You can see at a glance which pages produced contradictions or new discoveries.

### Research Summary
One click in the topbar triggers a full cross-session synthesis. The agent reads all saved research notes and produces:
- A multi-paragraph synthesis connecting all sources
- Key themes that emerged across the research
- Contradictions between sources
- Open questions that remain unexplored

### Session Management
Name your research sessions ("CRISPR research", "Climate policy"), export the full graph and all insights as JSON, and toggle the extension on/off without losing data.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Chrome Extension                    │
│                                                      │
│  Content Script → extracts page text after 15s      │
│  Background SW  → queues pages, saves to storage    │
│  Dashboard      → knowledge graph + insight feed    │
└──────────────────────┬──────────────────────────────┘
                       │ POST /process
                       ▼
┌─────────────────────────────────────────────────────┐
│           Python Agent Server  :3738                 │
│                                                      │
│  Guardrails (input validation)                       │
│  OrchestratorAgent                                   │
│  ├── ExtractorAgent (ReAct + RAG)                    │
│  │     ├── [MCP] search_notes  ← RAG recall         │
│  │     ├── LLM  ← extract entities + insights       │
│  │     ├── [MCP] write_file   ← persist note        │
│  │     └── [MCP] write_note   ← store entities      │
│  │                                                   │
│  ├── GraphAgent (ReAct)                              │
│  │     ├── [MCP] search_notes  ← look up entities   │
│  │     └── LLM  ← find contradictions + patterns    │
│  │                                                   │
│  └── MemoryAgent (async)                             │
│        └── [MCP] write_note   ← store page summary  │
│                                                      │
│  Guardrails (output validation)                      │
│  Observability (structured logs + trace + metrics)   │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
  basic-memory :8765         filesystem :8766
  (semantic recall / RAG)    (note persistence)
```

---

## MCP Tools

Two MCP servers run locally and are used by the agents via `langchain-mcp-adapters`.

### basic-memory — semantic memory store

| Tool | Used by | What it does |
|---|---|---|
| `search_notes` | ExtractorAgent, GraphAgent | RAG retrieval — searches prior knowledge before analyzing a new page |
| `write_note` | ExtractorAgent, MemoryAgent | Stores entity profiles and page summaries for future recall |

### filesystem — structured note persistence

| Tool | Used by | What it does |
|---|---|---|
| `write_file` | ExtractorAgent | Saves a full structured research note (entities, relationships, insights) |
| `read_file` | SynthesisAgent | Reads saved notes to generate cross-session synthesis |
| `list_directory` | SynthesisAgent | Enumerates all saved research notes |

---

## Agents

### ExtractorAgent `ReAct`
The core per-page agent. Runs for every page the user visits. Its system prompt drives a 4-step loop:

1. **Recall** — searches memory for prior context on this topic before reading anything (RAG)
2. **Analyze** — extracts entities, relationships, and insights informed by what it already knows
3. **Persist** — writes a structured note to the filesystem MCP
4. **Remember** — stores entity profiles in memory so future pages can find them

Insights are grounded: contradictions must name the conflicting source, patterns must reference at least 2 sources by name.

### GraphAgent `ReAct`
A second-pass agent that runs after extraction. Independently looks up each extracted entity in memory and enriches the result with cross-page contradictions, patterns, and inferred relationships the extractor may have missed.

### MemoryAgent
Dedicated agent for memory operations with two clean methods — `recall(query)` and `store(url, title, summary, entities)` — each backed by a ReAct loop with its own system prompt. Runs asynchronously after the main pipeline so it never blocks the response.

### SynthesisAgent `ReAct`
Triggered on demand by the Research Summary button. Uses the filesystem MCP to list and read all saved research notes, then produces a structured synthesis with key themes, contradictions, and open questions.

### OrchestratorAgent
Coordinates the pipeline: ExtractorAgent → GraphAgent in sequence, then fires MemoryAgent asynchronously. Controls concurrency via `asyncio.Semaphore(3)`.

---

## RAG — Retrieval-Augmented Generation

Every page is analyzed in the context of what ResearchMind already knows. Before the LLM extracts anything, the ExtractorAgent calls `search_notes` on the memory MCP server to retrieve semantically similar prior knowledge.

This retrieved context is injected directly into the LLM prompt — making every extraction RAG-augmented:

```
Page content  +  Retrieved memory  →  LLM  →  Grounded extraction
```

The result: contradictions are detected because the agent sees the conflicting prior claim. Patterns emerge because the agent recognizes the same entity appearing across sources. Without RAG, every page would be analyzed in isolation.

The `basic-memory` MCP server handles semantic indexing and retrieval. Entity profiles are stored with consistent naming (`entity:{name}`) so they can be found across sessions.

---

## Guardrails

`agents/guardrails.py` enforces safety and quality constraints at two points in the pipeline.

### Input guardrails (before processing)

| Check | What it does |
|---|---|
| Domain blocklist | Skips privacy-sensitive domains (banking, email, social media, auth pages) |
| Minimum word count | Skips pages with fewer than 100 words — not enough signal |
| Prompt injection stripping | Removes patterns like "ignore previous instructions" from page content before it reaches the LLM |
| Text length cap | Truncates input to 8000 chars to prevent token overflow |

### Output guardrails (after LLM extraction)

| Check | What it does |
|---|---|
| Schema enforcement | Validates that entities, relationships, and insights match expected structure |
| Type validation | Ensures entity types are one of: person, concept, claim, study, organization, date, place |
| List size caps | Max 10 entities, 8 relationships, 6 insights per page |
| Field length caps | All text fields capped at 500 chars |
| Null safety | Replaces missing or non-string values with safe defaults |

The server returns HTTP `422` for pages blocked by input guardrails, so the extension can log the skip reason without treating it as an error.

---

## Observability

`agents/observability.py` provides structured logging, per-pipeline tracing, and metrics — all without any external service.

### Structured logging
Every log line is emitted as a JSON object with timestamp, level, logger name, and contextual fields. Easy to pipe into any log aggregator (Datadog, Loki, CloudWatch).

```json
{"ts": "2025-04-29T08:17:00Z", "level": "INFO", "logger": "researchmind.trace",
 "msg": "[a3f1b2] ✓ pipeline complete",
 "extra": {"trace_id": "a3f1b2", "total_ms": 1842, "entities": 8, "insights": 4}}
```

### Pipeline tracing
Every page processing run gets a `trace_id`. Each agent stage is timed individually:

```
[a3f1b2] → ExtractorAgent        (started)
[a3f1b2] → GraphAgent            (started)
[a3f1b2] ✓ pipeline complete     total_ms=1842, stages=[{extractor: 1200ms}, {graph: 600ms}]
```

### Metrics endpoint
`GET /metrics` returns live counters for the running server:

```json
{
  "pages_processed": 42,
  "pages_skipped": 3,
  "pages_errored": 1,
  "total_entities": 318,
  "total_insights": 167,
  "avg_pipeline_ms": 1640.2
}
```

### HTTP request logging
Every request to the agent server is logged with method, path, status code, and duration.

---

## Tech Stack

| Layer | Tech |
|---|---|
| Extension framework | Plasmo + TypeScript (Manifest V3) |
| Knowledge graph UI | react-force-graph-2d (canvas-based, handles 500+ nodes) |
| State management | Zustand |
| Agent framework | LangChain + LangGraph (Python) |
| MCP integration | langchain-mcp-adapters |
| MCP servers | basic-memory · @modelcontextprotocol/server-filesystem |
| RAG retrieval | basic-memory semantic search (via MCP) |
| Guardrails | agents/guardrails.py — input + output validation |
| Observability | agents/observability.py — structured logs, traces, metrics |
| LLM — local | Ollama (qwen3:8b, llama3.1, mistral, gemma2, phi3, and more) |
| LLM — cloud | OpenAI GPT-4o/mini · Anthropic Claude Sonnet/Opus/Haiku |
| API server | FastAPI + uvicorn |
| Extension storage | chrome.storage.local (MV3 compatible) |
| Research notes | ~/ResearchMind/ (local filesystem) |

---

## Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Chrome
- One of: [Ollama](https://ollama.com) · OpenAI API key · Anthropic API key
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — for MCP servers (`pip install uv`)

---

### 1 — Clone and install

```bash
git clone https://github.com/vishwapandiyan/Research_mind.git
cd Research_mind

# Extension
npm install

# Python agents
cd agents
pip install -r requirements.txt
```

---

### 2 — Start MCP servers

```bash
cd agents
python3 start_mcp_servers.py
```

Starts `basic-memory` on `:8765` and `filesystem` on `:8766`. Keep this terminal open.

---

### 3 — Start the Python agent server

```bash
# new terminal
cd agents
python3 server.py
```

Expected output:
```
[ResearchMind] 🚀 Agent server starting...
INFO: Uvicorn running on http://127.0.0.1:3738
```

---

### 4 — Start Ollama (local LLM only)

```bash
# new terminal — skip if using OpenAI or Anthropic
ollama serve
ollama pull qwen3:8b
```

---

### 5 — Build and load the extension

```bash
# new terminal, from researchmind root
npm run dev
```

Then in Chrome:
1. Go to `chrome://extensions`
2. Enable **Developer mode** (top right toggle)
3. Click **Load unpacked**
4. Select `researchmind/build/chrome-mv3-dev`

---

### 6 — Configure your LLM

Click the ResearchMind icon in the Chrome toolbar:

| Tab | What to do |
|---|---|
| **Ollama** | Select a model. Make sure `ollama serve` is running. |
| **GPT** | Paste your OpenAI API key (`sk-...`), pick a model. |
| **Claude** | Paste your Anthropic API key (`sk-ant-...`), pick a model. |

The key is sent to the local Python server at runtime. It is never written to disk.

Get keys here:
- OpenAI: [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- Anthropic: [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys)

---

### 7 — Start researching

1. Click **Open Dashboard** in the popup
2. Browse any research page — Wikipedia, arXiv, news articles, documentation
3. Stay on the page for at least **15 seconds**
4. Watch the knowledge graph populate in real time

The extension processes pages silently. The dashboard updates as each page is analyzed.

---

### Monitor the pipeline

```bash
# Live metrics
curl http://localhost:3738/metrics

# Health + current LLM config
curl http://localhost:3738/health
```

---

## Environment variables (optional)

Copy `.env.example` to `.env` to set defaults without using the popup:

```bash
OLLAMA_MODEL=qwen3:8b
OLLAMA_BASE_URL=http://localhost:11434

# Can also be set via popup at runtime — never committed to git
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional — enables web search for gap-filling
BRAVE_API_KEY=...
```

---

## Privacy

| Mode | What leaves your machine |
|---|---|
| Ollama | Nothing. All processing is local. |
| OpenAI / Anthropic | Only extracted page text (not raw HTML) is sent to the API. |

Research notes are saved to `~/ResearchMind/` on your local filesystem. No telemetry, no accounts, no cloud sync.
