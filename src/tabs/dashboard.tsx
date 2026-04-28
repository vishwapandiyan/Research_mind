import React, { useEffect } from "react"
import { InsightFeed } from "../dashboard/components/InsightFeed"
import { KnowledgeGraph } from "../dashboard/components/KnowledgeGraph"
import { SourceFeed } from "../dashboard/components/SourceFeed"
import { Topbar } from "../dashboard/components/Topbar"
import { useResearchStore } from "../dashboard/stores/researchStore"

import "./dashboard.css"

function Dashboard() {
  const { loadAll, addReading, setActive, setHasApiKey } = useResearchStore()

  useEffect(() => {
    console.log("[Dashboard] 🚀 Initializing...")
    loadAll()

    chrome.runtime.sendMessage({ type: "GET_STATE" }, (res) => {
      if (res) {
        console.log("[Dashboard] 📡 Got state:", res)
        setActive(res.active ?? true)
        setHasApiKey(res.hasApiKey ?? false)
      }
    })

    // Listen for live broadcasts from background
    const listener = (message: any) => {
      console.log("[Dashboard] 📨 Received message:", message)
      if (message.type === "READING_ADDED") addReading(message.payload)
    }
    chrome.runtime.onMessage.addListener(listener)

    // Poll chrome.storage.local every 10s to catch any missed broadcasts
    const poll = setInterval(() => {
      console.log("[Dashboard] ⏰ Polling storage...")
      loadAll()
    }, 10000)

    return () => {
      chrome.runtime.onMessage.removeListener(listener)
      clearInterval(poll)
    }
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

export default Dashboard
