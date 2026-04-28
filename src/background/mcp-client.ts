/**
 * MCP Client — communicates with local MCP servers via HTTP (bridge pattern).
 * MCP servers run locally; this client calls a local bridge at localhost:3737.
 * Falls back gracefully if servers are unavailable.
 */

const MCP_BRIDGE_URL = "http://localhost:3737"

export interface MCPMemoryEntry {
  key: string
  content: string
}

async function mcpCall(server: string, tool: string, args: Record<string, unknown>) {
  try {
    const res = await fetch(`${MCP_BRIDGE_URL}/${server}/${tool}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(args),
      signal: AbortSignal.timeout(5000)
    })
    if (!res.ok) return null
    return await res.json()
  } catch {
    // MCP server not running — degrade gracefully
    return null
  }
}

export const memoryMCP = {
  async write(key: string, content: string) {
    return mcpCall("memory", "write", { key, content })
  },
  async search(query: string): Promise<MCPMemoryEntry[]> {
    const result = await mcpCall("memory", "search", { query })
    return result?.entries ?? []
  }
}

export const searchMCP = {
  async web(query: string, count = 5) {
    const result = await mcpCall("search", "web", { query, count })
    return result?.results ?? []
  }
}

export const fsMCP = {
  async write(path: string, content: string) {
    return mcpCall("fs", "write", { path, content })
  },
  async read(path: string) {
    return mcpCall("fs", "read", { path })
  }
}
