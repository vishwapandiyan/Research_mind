import React, { useEffect } from "react"
import { createRoot } from "react-dom/client"
import { InsightFeed } from "./components/InsightFeed"
import { KnowledgeGraph } from "./components/KnowledgeGraph"
import { SourceFeed } from "./components/SourceFeed"
import { Topbar } from "./components/Topbar"
import { useResearchStore } from "./stores/researchStore"

function Dashboard() {
  const { loadAll, addReading, setActive, setHasApiKey } = useResearchStore()

  useEffect(() => {
    loadAll()

    // Get initial state from background
    chrome.runtime.sendMessage({ type: "GET_STATE" }, (res) => {
      if (res) {
        setActive(res.active ?? true)
        setHasApiKey(res.hasApiKey ?? false)
      }
    })

    // Listen for live updates from background
    const listener = (message: any) => {
      if (message.type === "READING_ADDED") {
        addReading(message.payload)
      }
    }
    chrome.runtime.onMessage.addListener(listener)
    return () => chrome.runtime.onMessage.removeListener(listener)
  }, [])

  return (
    <div style={styles.root}>
      <Topbar />
      <div style={styles.main}>
        <SourceFeed />
        <KnowledgeGraph />
        <InsightFeed />
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    width: "100vw",
    height: "100vh",
    display: "flex",
    flexDirection: "column",
    background: "#0f172a",
    fontFamily: "system-ui, -apple-system, sans-serif",
    overflow: "hidden"
  },
  main: { display: "flex", flex: 1, overflow: "hidden" }
}

const root = createRoot(document.getElementById("root")!)
root.render(<Dashboard />)
