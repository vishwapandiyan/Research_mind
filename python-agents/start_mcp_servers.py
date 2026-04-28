"""
Starts MCP servers in HTTP (streamable-http) mode.
Run this FIRST before starting the agent server.

  python3.13 start_mcp_servers.py
"""
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

RESEARCH_DIR = str(Path.home() / "ResearchMind")

servers = [
    {
        "name": "basic-memory",
        "cmd": ["uvx", "basic-memory", "mcp",
                "--transport", "streamable-http",
                "--port", "8765"],
        "port": 8765,
    },
    {
        "name": "filesystem",
        "cmd": ["npx", "-y", "@modelcontextprotocol/server-filesystem",
                RESEARCH_DIR],
        "port": 8766,
        "env_extra": {
            "MCP_TRANSPORT": "streamable-http",
            "MCP_PORT": "8766"
        }
    },
]

procs = []
import os
for s in servers:
    print(f"[MCP Servers] Starting {s['name']} on port {s['port']}...")
    env = {**os.environ, **s.get("env_extra", {})}
    p = subprocess.Popen(s["cmd"], env=env,
                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    procs.append((s["name"], s["port"], p))

print("[MCP Servers] Waiting for servers to initialize (5s)...")
time.sleep(5)

for name, port, p in procs:
    if p.poll() is not None:
        err = p.stderr.read().decode()[:300]
        print(f"[MCP Servers] ⚠️  {name} exited: {err}")
    else:
        try:
            urllib.request.urlopen(f"http://localhost:{port}/mcp", timeout=2)
        except Exception:
            pass  # expected — just checking it's alive
        print(f"[MCP Servers] ✅ {name} running on port {port} (pid {p.pid})")

print("\n[MCP Servers] Ready. Now run in another terminal:")
print("  python3.13 server.py\n")

try:
    for _, _, p in procs:
        p.wait()
except KeyboardInterrupt:
    print("\n[MCP Servers] Shutting down...")
    for _, _, p in procs:
        p.terminate()
