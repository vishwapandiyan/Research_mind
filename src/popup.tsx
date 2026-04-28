import React, { useEffect, useState } from "react"

type Provider = "ollama" | "openai" | "anthropic"

const OPENAI_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]
const ANTHROPIC_MODELS = ["claude-sonnet-4-5", "claude-opus-4-5", "claude-haiku-3-5"]
const OLLAMA_MODELS = ["qwen3:8b", "qwen3:14b", "qwen3:32b", "llama3.1", "mistral", "mixtral", "gemma2", "phi3"]

interface AgentConfig {
  provider: Provider
  openai_model: string
  anthropic_model: string
  ollama_model: string
  has_api_key: boolean
}

const PYTHON = "http://localhost:3738"

function Popup() {
  const [active, setActive] = useState(true)
  const [config, setConfig] = useState<AgentConfig>({
    provider: "ollama",
    openai_model: "gpt-4o",
    anthropic_model: "claude-sonnet-4-5",
    ollama_model: "qwen3:8b",
    has_api_key: false,
  })
  const [apiKey, setApiKey] = useState("")
  const [showKey, setShowKey] = useState(false)
  const [agentOk, setAgentOk] = useState<boolean | null>(null)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    chrome.runtime.sendMessage({ type: "GET_STATE" }, (res) => {
      if (res?.active !== undefined) setActive(res.active)
    })
    checkAgent()
  }, [])

  async function checkAgent() {
    setAgentOk(null)
    try {
      const res = await fetch(`${PYTHON}/health`, { signal: AbortSignal.timeout(2000) })
      if (res.ok) {
        const data = await res.json()
        setConfig((c) => ({ ...c, ...data }))
        setAgentOk(true)
      } else {
        setAgentOk(false)
      }
    } catch {
      setAgentOk(false)
    }
  }

  async function saveConfig(overrides: Partial<AgentConfig> & { api_key?: string } = {}) {
    const merged = { ...config, ...overrides }
    setSaving(true)
    setSaved(false)
    try {
      const body: Record<string, string> = {
        provider: merged.provider,
        openai_model: merged.openai_model,
        anthropic_model: merged.anthropic_model,
        ollama_model: merged.ollama_model,
      }
      if (overrides.api_key !== undefined) body.api_key = overrides.api_key
      const res = await fetch(`${PYTHON}/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(3000),
      })
      if (res.ok) {
        const data = await res.json()
        setConfig((c) => ({ ...c, ...data }))
        setSaved(true)
        setShowKey(false)
        setApiKey("")
        setTimeout(() => setSaved(false), 2000)
      }
    } catch {
      // agent not running — save locally anyway
      setConfig((c) => ({ ...c, ...overrides }))
    } finally {
      setSaving(false)
    }
    // persist to chrome storage so background can read it
    chrome.runtime.sendMessage({ type: "SET_CONFIG", ...merged })
  }

  function toggle() {
    const next = !active
    setActive(next)
    chrome.runtime.sendMessage({ type: "SET_ACTIVE", active: next })
  }

  const needsKey = config.provider !== "ollama"
  const currentModel =
    config.provider === "openai" ? config.openai_model
    : config.provider === "anthropic" ? config.anthropic_model
    : config.ollama_model
  const modelList =
    config.provider === "openai" ? OPENAI_MODELS
    : config.provider === "anthropic" ? ANTHROPIC_MODELS
    : OLLAMA_MODELS

  return (
    <div style={s.root}>
      {/* Header */}
      <div style={s.header}>
        <span style={s.logo}>🧠 ResearchMind</span>
        <button style={{ ...s.toggle, background: active ? "#22c55e" : "#475569" }} onClick={toggle}>
          {active ? "ON" : "OFF"}
        </button>
      </div>

      {/* Agent status */}
      <div style={{ ...s.statusRow, color: agentOk === null ? "#64748b" : agentOk ? "#22c55e" : "#ef4444" }}>
        <span>{agentOk === null ? "⏳" : agentOk ? "✅" : "❌"}</span>
        <span>Python agent {agentOk === null ? "checking..." : agentOk ? "running" : "not running"}</span>
        {agentOk === false && (
          <button style={s.retryBtn} onClick={checkAgent}>retry</button>
        )}
      </div>
      {agentOk === false && (
        <div style={s.warning}>
          <code style={s.code}>python3 agents/server.py</code>
        </div>
      )}

      {/* Provider tabs */}
      <div style={s.section}>
        <div style={s.label}>LLM Provider</div>
        <div style={s.tabs}>
          {(["ollama", "openai", "anthropic"] as Provider[]).map((p) => (
            <button
              key={p}
              style={{
                ...s.tab,
                background: config.provider === p ? providerColor(p) : "#1e293b",
                fontWeight: config.provider === p ? 700 : 400,
              }}
              onClick={() => saveConfig({ provider: p })}>
              {providerLabel(p)}
            </button>
          ))}
        </div>
      </div>

      {/* Model selector */}
      <div style={s.section}>
        <div style={s.label}>Model</div>
        <select
          style={s.select}
          value={currentModel}
          onChange={(e) => {
            const key =
              config.provider === "openai" ? "openai_model"
              : config.provider === "anthropic" ? "anthropic_model"
              : "ollama_model"
            saveConfig({ [key]: e.target.value } as any)
          }}>
          {modelList.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        {config.provider === "ollama" && (
          <div style={s.hint}>Requires <code style={s.code}>ollama serve</code></div>
        )}
      </div>

      {/* API key (OpenAI / Anthropic) */}
      {needsKey && (
        <div style={s.section}>
          <div style={s.label}>
            {config.provider === "openai" ? "OpenAI" : "Anthropic"} API Key
          </div>
          {showKey ? (
            <div style={s.row}>
              <input
                style={s.input}
                type="password"
                placeholder={config.provider === "openai" ? "sk-..." : "sk-ant-..."}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && saveConfig({ api_key: apiKey.trim() })}
                autoFocus
              />
              <button
                style={{ ...s.saveBtn, opacity: saving ? 0.6 : 1 }}
                onClick={() => saveConfig({ api_key: apiKey.trim() })}
                disabled={saving}>
                {saving ? "..." : "Save"}
              </button>
            </div>
          ) : (
            <button style={s.btn} onClick={() => setShowKey(true)}>
              {config.has_api_key ? "✓ Key saved — update" : "Paste API key"}
            </button>
          )}
          {saved && <div style={{ color: "#22c55e", fontSize: 11 }}>✓ Saved</div>}
          <div style={s.hint}>
            {config.provider === "openai"
              ? "Get key: platform.openai.com/api-keys"
              : "Get key: console.anthropic.com/settings/keys"}
          </div>
        </div>
      )}

      <button style={{ ...s.btn, ...s.dashBtn }} onClick={() =>
        chrome.tabs.create({ url: chrome.runtime.getURL("tabs/dashboard.html") })
      }>
        Open Dashboard →
      </button>
    </div>
  )
}

function providerColor(p: Provider) {
  return p === "openai" ? "#16a34a" : p === "anthropic" ? "#7c3aed" : "#2563eb"
}
function providerLabel(p: Provider) {
  return p === "openai" ? "GPT" : p === "anthropic" ? "Claude" : "Ollama"
}

const s: Record<string, React.CSSProperties> = {
  root: { width: 280, padding: 14, background: "#0f172a", fontFamily: "system-ui, sans-serif", display: "flex", flexDirection: "column", gap: 10 },
  header: { display: "flex", alignItems: "center", justifyContent: "space-between" },
  logo: { color: "#e2e8f0", fontWeight: 700, fontSize: 15 },
  toggle: { color: "#fff", border: "none", borderRadius: 6, padding: "4px 12px", cursor: "pointer", fontWeight: 700, fontSize: 12 },
  statusRow: { display: "flex", alignItems: "center", gap: 6, fontSize: 12 },
  retryBtn: { background: "none", border: "1px solid #334155", color: "#94a3b8", borderRadius: 4, padding: "1px 6px", cursor: "pointer", fontSize: 11 },
  warning: { background: "#1e293b", border: "1px solid #334155", borderRadius: 6, padding: "8px 10px" },
  code: { background: "#0f172a", padding: "2px 4px", borderRadius: 3, color: "#22c55e", fontFamily: "monospace", fontSize: 11 },
  section: { display: "flex", flexDirection: "column", gap: 5 },
  label: { color: "#64748b", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: 0.5 },
  tabs: { display: "flex", gap: 4 },
  tab: { flex: 1, color: "#e2e8f0", border: "none", borderRadius: 6, padding: "6px 4px", cursor: "pointer", fontSize: 12 },
  select: { background: "#1e293b", border: "1px solid #334155", borderRadius: 6, color: "#e2e8f0", padding: "5px 8px", fontSize: 12 },
  hint: { color: "#475569", fontSize: 10 },
  row: { display: "flex", gap: 6 },
  input: { flex: 1, background: "#1e293b", border: "1px solid #334155", borderRadius: 6, color: "#e2e8f0", padding: "5px 8px", fontSize: 12 },
  saveBtn: { background: "#3b82f6", color: "#fff", border: "none", borderRadius: 6, padding: "5px 10px", cursor: "pointer", fontSize: 12 },
  btn: { background: "#1e293b", color: "#e2e8f0", border: "1px solid #334155", borderRadius: 6, padding: "7px 12px", cursor: "pointer", fontSize: 12, width: "100%", textAlign: "center" },
  dashBtn: { background: "#3b82f6", border: "none", fontWeight: 600 },
}

export default Popup
