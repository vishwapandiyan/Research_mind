import React, { useState } from "react"
import { useResearchStore } from "../stores/researchStore"

export function Topbar() {
  const { isActive, hasApiKey, sessionLabel, setActive, setSessionLabel, setHasApiKey } =
    useResearchStore()
  const [apiKeyInput, setApiKeyInput] = useState("")
  const [showApiInput, setShowApiInput] = useState(false)
  const [synthesizing, setSynthesizing] = useState(false)
  const [synthesis, setSynthesis] = useState("")

  function toggleActive() {
    const next = !isActive
    setActive(next)
    chrome.runtime.sendMessage({ type: "SET_ACTIVE", active: next })
  }

  function saveApiKey() {
    if (!apiKeyInput.trim()) return
    chrome.runtime.sendMessage({ type: "SET_API_KEY", apiKey: apiKeyInput.trim() }, () => {
      setHasApiKey(true)
      setShowApiInput(false)
      setApiKeyInput("")
    })
  }

  async function handleSynthesize() {
    setSynthesizing(true)
    console.log("[Dashboard] 🔄 Requesting synthesis...")
    chrome.runtime.sendMessage({ type: "SYNTHESIZE" }, (res) => {
      console.log("[Dashboard] 📨 Synthesis response:", res)
      if (res?.summary) {
        setSynthesis(res.summary)
        console.log("[Dashboard] ✅ Synthesis received")
      } else {
        setSynthesis("No summary available. Make sure you have research notes saved.")
        console.warn("[Dashboard] ⚠️  No summary in response")
      }
      setSynthesizing(false)
    })
  }

  function exportData() {
    const state = useResearchStore.getState()
    const data = {
      session: state.sessionLabel,
      readings: state.readings,
      entities: state.entities,
      insights: state.insights
    }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `researchmind-${Date.now()}.json`
    a.click()
  }

  return (
    <div style={styles.bar}>
      <div style={styles.left}>
        <span style={styles.logo}>🧠 ResearchMind</span>
        <input
          style={styles.sessionInput}
          value={sessionLabel}
          onChange={(e) => setSessionLabel(e.target.value)}
          placeholder="Session name..."
        />
      </div>

      <div style={styles.right}>
        {synthesis && (
          <div style={styles.synthesisPopup}>
            <p style={{ margin: 0, fontSize: 13 }}>{synthesis}</p>
            <button style={styles.closeBtn} onClick={() => setSynthesis("")}>✕</button>
          </div>
        )}

        <button style={styles.btn} onClick={handleSynthesize} disabled={synthesizing}>
          {synthesizing ? "Synthesizing..." : "Research Summary"}
        </button>

        <button style={styles.btn} onClick={exportData}>Export</button>

        {showApiInput ? (
          <span style={{ display: "flex", gap: 4 }}>
            <input
              style={styles.apiInput}
              type="password"
              placeholder="sk-ant-..."
              value={apiKeyInput}
              onChange={(e) => setApiKeyInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && saveApiKey()}
            />
            <button style={styles.btn} onClick={saveApiKey}>Save</button>
            <button style={styles.btn} onClick={() => setShowApiInput(false)}>✕</button>
          </span>
        ) : (
          <button
            style={{ ...styles.btn, background: hasApiKey ? "#22c55e" : "#f59e0b" }}
            onClick={() => setShowApiInput(true)}>
            {hasApiKey ? "API Key ✓" : "Set API Key"}
          </button>
        )}

        <button
          style={{ ...styles.toggleBtn, background: isActive ? "#22c55e" : "#6b7280" }}
          onClick={toggleActive}>
          {isActive ? "ON" : "OFF"}
        </button>
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  bar: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "10px 16px",
    background: "#0f172a",
    borderBottom: "1px solid #1e293b",
    position: "relative",
    zIndex: 10
  },
  left: { display: "flex", alignItems: "center", gap: 12 },
  right: { display: "flex", alignItems: "center", gap: 8 },
  logo: { color: "#e2e8f0", fontWeight: 700, fontSize: 16 },
  sessionInput: {
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: 6,
    color: "#e2e8f0",
    padding: "4px 8px",
    fontSize: 13,
    width: 200
  },
  btn: {
    background: "#334155",
    color: "#e2e8f0",
    border: "none",
    borderRadius: 6,
    padding: "5px 10px",
    cursor: "pointer",
    fontSize: 12
  },
  toggleBtn: {
    color: "#fff",
    border: "none",
    borderRadius: 6,
    padding: "5px 12px",
    cursor: "pointer",
    fontWeight: 700,
    fontSize: 13
  },
  apiInput: {
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: 6,
    color: "#e2e8f0",
    padding: "4px 8px",
    fontSize: 12,
    width: 180
  },
  synthesisPopup: {
    position: "absolute",
    top: 56,
    right: 16,
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: 8,
    padding: 12,
    maxWidth: 400,
    color: "#e2e8f0",
    zIndex: 100
  },
  closeBtn: {
    position: "absolute",
    top: 6,
    right: 8,
    background: "none",
    border: "none",
    color: "#94a3b8",
    cursor: "pointer",
    fontSize: 14
  }
}
