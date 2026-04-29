"""
Starts MCP servers in HTTP (streamable-http) mode.

Only the filesystem MCP is needed now.
Memory/recall is handled by the RAG vector store (ChromaDB + embeddings).

Prerequisites:
  ollama pull nomic-embed-text   ← embedding model for RAG (local)

Run this FIRST, then start the agent server:
  python3 start_mcp_servers.py
  python3 server.py
"""
import os
import subprocess
import time
import urllib.request
from pathlib import Path

RESEARCH_DIR = str(Path.home() / "ResearchMind")

servers = [
    {
        "name": "filesystem",
        "cmd": ["npx", "-y", "@modelcontextprotocol/server-filesystem", RESEARCH_DIR],
        "port": 8766,
        "env_extra": {
            "MCP_TRANSPORT": "streamable-http",
            "MCP_PORT": "8766",
        },
    },
]

procs = []
for s in servers:
    print(f"[MCP] Starting {s['name']} on port {s['port']}...")
    env = {**os.environ, **s.get("env_extra", {})}
    p = subprocess.Popen(
        s["cmd"], env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
    )
    procs.append((s["name"], s["port"], p))

print("[MCP] Waiting 5s for servers to initialize...")
time.sleep(5)

for name, port, p in procs:
    if p.poll() is not None:
        err = p.stderr.read().decode()[:300]
        print(f"[MCP] ⚠️  {name} exited early: {err}")
    else:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/mcp", timeout=2)
        except Exception:
            pass
        print(f"[MCP] ✅ {name} running on port {port} (pid {p.pid})")

print("\n[MCP] Ready.")
print("  RAG vector store: ChromaDB at ~/ResearchMind/.chroma")
print("  Embedding model:  nomic-embed-text (via Ollama)")
print("\nNow run: python3 server.py\n")

try:
    for _, _, p in procs:
        p.wait()
except KeyboardInterrupt:
    print("\n[MCP] Shutting down...")
    for _, _, p in procs:
        p.terminate()
