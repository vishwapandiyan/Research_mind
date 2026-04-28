import React, { useState } from "react"
import type { Insight } from "../../shared/types"
import { useResearchStore } from "../stores/researchStore"

const INSIGHT_ICONS: Record<Insight["type"], string> = {
  discovery: "🔍",
  contradiction: "⚡",
  pattern: "🔗",
  gap: "❓"
}

const INSIGHT_COLORS: Record<Insight["type"], string> = {
  discovery: "#3b82f6",
  contradiction: "#ef4444",
  pattern: "#8b5cf6",
  gap: "#f59e0b"
}

type FilterType = Insight["type"] | "all"

function InsightCard({ insight }: { insight: Insight }) {
  return (
    <div style={{ ...styles.card, borderLeft: `3px solid ${INSIGHT_COLORS[insight.type]}` }}>
      <div style={styles.cardHeader}>
        <span>{INSIGHT_ICONS[insight.type]}</span>
        <span style={{ ...styles.typeBadge, color: INSIGHT_COLORS[insight.type] }}>
          {insight.type}
        </span>
        <span style={styles.time}>{new Date(insight.createdAt).toLocaleTimeString()}</span>
      </div>
      <p style={styles.text}>{insight.text}</p>
      {insight.sourcePages.length > 0 && (
        <div style={styles.sources}>
          {insight.sourcePages.slice(0, 2).map((url) => {
            try {
              return (
                <a key={url} href={url} target="_blank" rel="noreferrer" style={styles.sourceLink}>
                  {new URL(url).hostname}
                </a>
              )
            } catch {
              return null
            }
          })}
        </div>
      )}
    </div>
  )
}

export function InsightFeed() {
  const { insights } = useResearchStore()
  const [filter, setFilter] = useState<FilterType>("all")

  const filtered = filter === "all" ? insights : insights.filter((i) => i.type === filter)

  const counts = {
    discovery: insights.filter((i) => i.type === "discovery").length,
    contradiction: insights.filter((i) => i.type === "contradiction").length,
    pattern: insights.filter((i) => i.type === "pattern").length,
    gap: insights.filter((i) => i.type === "gap").length
  }

  const filters: FilterType[] = ["all", "discovery", "contradiction", "pattern", "gap"]

  return (
    <div style={styles.panel}>
      <div style={styles.header}>Insights ({insights.length})</div>

      <div style={styles.filterRow}>
        {filters.map((f) => (
          <button
            key={f}
            style={{
              ...styles.filterBtn,
              background: filter === f ? "#334155" : "transparent",
              color:
                f === "all" ? "#e2e8f0" : INSIGHT_COLORS[f as Insight["type"]] ?? "#e2e8f0"
            }}
            onClick={() => setFilter(f)}>
            {f === "all" ? `All (${insights.length})` : `${INSIGHT_ICONS[f as Insight["type"]]} ${f} (${counts[f as Insight["type"]]})`}
          </button>
        ))}
      </div>

      <div style={styles.list}>
        {filtered.length === 0 && (
          <div style={styles.empty}>
            Insights will appear here as the agent analyzes your browsing.
          </div>
        )}
        {filtered.map((i) => (
          <InsightCard key={i.id} insight={i} />
        ))}
      </div>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    width: 300,
    minWidth: 300,
    background: "#0f172a",
    borderLeft: "1px solid #1e293b",
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
  filterRow: {
    display: "flex",
    flexWrap: "wrap",
    gap: 4,
    padding: "8px 12px",
    borderBottom: "1px solid #1e293b"
  },
  filterBtn: {
    border: "none",
    borderRadius: 4,
    padding: "2px 8px",
    cursor: "pointer",
    fontSize: 11,
    fontWeight: 500
  },
  list: { overflowY: "auto", flex: 1 },
  card: {
    padding: "10px 14px",
    borderBottom: "1px solid #1e293b",
    marginLeft: 0
  },
  cardHeader: {
    display: "flex",
    alignItems: "center",
    gap: 6,
    marginBottom: 6
  },
  typeBadge: {
    fontSize: 11,
    fontWeight: 600,
    textTransform: "capitalize"
  },
  time: { color: "#475569", fontSize: 10, marginLeft: "auto" },
  text: { color: "#cbd5e1", fontSize: 12, margin: "0 0 6px", lineHeight: 1.6 },
  sources: { display: "flex", gap: 6, flexWrap: "wrap" },
  sourceLink: { color: "#64748b", fontSize: 10, textDecoration: "none" },
  empty: { color: "#475569", fontSize: 13, padding: 16, lineHeight: 1.6 }
}
