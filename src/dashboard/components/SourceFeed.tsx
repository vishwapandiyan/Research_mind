import React from "react"
import type { PageReading } from "../../shared/types"
import { useResearchStore } from "../stores/researchStore"

const TAG_COLORS: Record<string, string> = {
  discovery: "#3b82f6",
  contradiction: "#ef4444",
  pattern: "#8b5cf6",
  gap: "#f59e0b"
}

function ReadingCard({ reading }: { reading: PageReading }) {
  const tags = reading.insights.map((i) => i.type)
  const uniqueTags = Array.from(new Set(tags))

  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <img
          src={`https://www.google.com/s2/favicons?domain=${reading.domain}&sz=16`}
          width={16}
          height={16}
          style={{ borderRadius: 2 }}
          alt=""
        />
        <a href={reading.url} target="_blank" rel="noreferrer" style={styles.title}>
          {reading.title || reading.url}
        </a>
      </div>
      <div style={styles.domain}>{reading.domain}</div>
      <p style={styles.summary}>{reading.summary}</p>
      <div style={styles.tags}>
        {uniqueTags.map((tag) => (
          <span key={tag} style={{ ...styles.tag, background: TAG_COLORS[tag] ?? "#475569" }}>
            {tag}
          </span>
        ))}
        <span style={styles.time}>{new Date(reading.readAt).toLocaleTimeString()}</span>
      </div>
    </div>
  )
}

export function SourceFeed() {
  const { readings, loading } = useResearchStore()

  return (
    <div style={styles.panel}>
      <div style={styles.header}>Sources ({readings.length})</div>
      {loading && <div style={styles.empty}>Loading...</div>}
      {!loading && readings.length === 0 && (
        <div style={styles.empty}>
          Browse any article or research page to start building your knowledge graph.
        </div>
      )}
      <div style={styles.list}>
        {readings.map((r) => (
          <ReadingCard key={r.id} reading={r} />
        ))}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 280,
    minWidth: 280,
    background: "#0f172a",
    borderRight: "1px solid #1e293b",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden"
  },
  header: {
    padding: "12px 16px",
    color: "#94a3b8",
    fontSize: 12,
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: 1,
    borderBottom: "1px solid #1e293b"
  },
  list: { overflowY: "auto", flex: 1 },
  card: {
    padding: "12px 16px",
    borderBottom: "1px solid #1e293b",
    cursor: "default"
  },
  cardHeader: { display: "flex", alignItems: "center", gap: 6, marginBottom: 4 },
  title: {
    color: "#e2e8f0",
    fontSize: 13,
    fontWeight: 500,
    textDecoration: "none",
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
    maxWidth: 210
  },
  domain: { color: "#64748b", fontSize: 11, marginBottom: 6 },
  summary: { color: "#94a3b8", fontSize: 12, margin: "0 0 8px", lineHeight: 1.5 },
  tags: { display: "flex", gap: 4, flexWrap: "wrap", alignItems: "center" },
  tag: {
    color: "#fff",
    fontSize: 10,
    padding: "2px 6px",
    borderRadius: 4,
    fontWeight: 600,
    textTransform: "capitalize"
  },
  time: { color: "#475569", fontSize: 10, marginLeft: "auto" },
  empty: { color: "#475569", fontSize: 13, padding: 16, lineHeight: 1.6 }
}
