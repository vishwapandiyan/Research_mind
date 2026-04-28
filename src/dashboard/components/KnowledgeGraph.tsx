import React, { useCallback, useMemo, useRef, useState } from "react"
import ForceGraph2D from "react-force-graph-2d"
import type { Entity } from "../../shared/types"
import { useResearchStore } from "../stores/researchStore"

const NODE_COLORS: Record<Entity["type"], string> = {
  person: "#3b82f6",
  concept: "#8b5cf6",
  claim: "#f59e0b",
  study: "#22c55e",
  organization: "#ec4899",
  date: "#64748b",
  place: "#06b6d4"
}

interface GraphNode {
  id: string
  name: string
  type: Entity["type"]
  val: number
}

interface GraphLink {
  source: string
  target: string
  label: string
}

export function KnowledgeGraph() {
  const { entities } = useResearchStore()
  const [selectedNode, setSelectedNode] = useState<Entity | null>(null)
  const [filterType, setFilterType] = useState<Entity["type"] | "all">("all")
  const fgRef = useRef<any>(null)

  const { nodes, links } = useMemo(() => {
    const filtered =
      filterType === "all" ? entities : entities.filter((e) => e.type === filterType)

    const nodeIds = new Set(filtered.map((e) => e.id))

    const nodes: GraphNode[] = filtered.map((e) => ({
      id: e.id,
      name: e.name,
      type: e.type,
      val: Math.max(1, e.seenOnPages.length * 2)
    }))

    const links: GraphLink[] = []
    for (const e of filtered) {
      for (const r of e.relationships) {
        // Find target entity by name
        const target = entities.find((en) => en.name === r.to)
        if (target && nodeIds.has(target.id)) {
          links.push({ source: e.id, target: target.id, label: r.label })
        }
      }
    }

    return { nodes, links }
  }, [entities, filterType])

  const handleNodeClick = useCallback(
    (node: GraphNode) => {
      const entity = entities.find((e) => e.id === node.id)
      setSelectedNode(entity ?? null)
    },
    [entities]
  )

  const entityTypes: Array<Entity["type"] | "all"> = [
    "all", "person", "concept", "claim", "study", "organization", "date", "place"
  ]

  return (
    <div style={styles.panel}>
      <div style={styles.header}>
        <span>Knowledge Graph ({nodes.length} nodes)</span>
        <div style={styles.filters}>
          {entityTypes.map((t) => (
            <button
              key={t}
              style={{
                ...styles.filterBtn,
                background: filterType === t ? "#334155" : "transparent",
                color: t === "all" ? "#e2e8f0" : NODE_COLORS[t as Entity["type"]] ?? "#e2e8f0"
              }}
              onClick={() => setFilterType(t)}>
              {t}
            </button>
          ))}
        </div>
      </div>

      <div style={styles.graphArea}>
        {nodes.length === 0 ? (
          <div style={styles.empty}>Knowledge graph will appear here as you browse.</div>
        ) : (
          <ForceGraph2D
            ref={fgRef}
            graphData={{ nodes, links }}
            nodeLabel="name"
            nodeColor={(n: any) => NODE_COLORS[(n as GraphNode).type] ?? "#94a3b8"}
            nodeVal={(n: any) => (n as GraphNode).val}
            linkLabel={(l: any) => (l as GraphLink).label}
            linkColor={() => "#334155"}
            onNodeClick={handleNodeClick}
            backgroundColor="#0f172a"
            width={undefined}
            height={undefined}
          />
        )}
      </div>

      {selectedNode && (
        <div style={styles.nodeDetail}>
          <div style={styles.nodeDetailHeader}>
            <span
              style={{
                ...styles.typeBadge,
                background: NODE_COLORS[selectedNode.type]
              }}>
              {selectedNode.type}
            </span>
            <strong style={{ color: "#e2e8f0" }}>{selectedNode.name}</strong>
            <button style={styles.closeBtn} onClick={() => setSelectedNode(null)}>✕</button>
          </div>
          <p style={styles.nodeDesc}>{selectedNode.description}</p>
          <div style={styles.nodePages}>
            <span style={styles.label}>Seen on {selectedNode.seenOnPages.length} page(s):</span>
            {selectedNode.seenOnPages.slice(0, 3).map((url) => (
              <a key={url} href={url} target="_blank" rel="noreferrer" style={styles.pageLink}>
                {new URL(url).hostname}
              </a>
            ))}
          </div>
          {selectedNode.relationships.length > 0 && (
            <div style={styles.rels}>
              <span style={styles.label}>Relationships:</span>
              {selectedNode.relationships.slice(0, 5).map((r, i) => (
                <div key={i} style={styles.rel}>
                  {r.from} → <em>{r.label}</em> → {r.to}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    flex: 1,
    background: "#0f172a",
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
    position: "relative"
  },
  header: {
    padding: "10px 16px",
    color: "#94a3b8",
    fontSize: 12,
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: 1,
    borderBottom: "1px solid #1e293b",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    flexWrap: "wrap",
    gap: 8
  },
  filters: { display: "flex", gap: 4, flexWrap: "wrap" },
  filterBtn: {
    border: "none",
    borderRadius: 4,
    padding: "2px 8px",
    cursor: "pointer",
    fontSize: 11,
    fontWeight: 500
  },
  graphArea: { flex: 1, overflow: "hidden" },
  empty: {
    color: "#475569",
    fontSize: 13,
    padding: 32,
    textAlign: "center",
    marginTop: 80
  },
  nodeDetail: {
    position: "absolute",
    bottom: 16,
    left: 16,
    background: "#1e293b",
    border: "1px solid #334155",
    borderRadius: 8,
    padding: 12,
    maxWidth: 320,
    zIndex: 10
  },
  nodeDetailHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 8
  },
  typeBadge: {
    color: "#fff",
    fontSize: 10,
    padding: "2px 6px",
    borderRadius: 4,
    fontWeight: 600,
    textTransform: "capitalize"
  },
  closeBtn: {
    marginLeft: "auto",
    background: "none",
    border: "none",
    color: "#94a3b8",
    cursor: "pointer",
    fontSize: 14
  },
  nodeDesc: { color: "#94a3b8", fontSize: 12, margin: "0 0 8px", lineHeight: 1.5 },
  nodePages: { display: "flex", flexDirection: "column", gap: 2, marginBottom: 8 },
  label: { color: "#64748b", fontSize: 11, marginBottom: 4 },
  pageLink: { color: "#3b82f6", fontSize: 11, textDecoration: "none" },
  rels: { display: "flex", flexDirection: "column", gap: 2 },
  rel: { color: "#94a3b8", fontSize: 11 }
}
