import { create } from "zustand"
import { getAllEntities, getAllInsights, getAllReadings } from "../../shared/storage"
import type { Entity, Insight, PageReading } from "../../shared/types"

interface ResearchState {
  readings: PageReading[]
  entities: Entity[]
  insights: Insight[]
  isActive: boolean
  hasApiKey: boolean
  sessionLabel: string
  loading: boolean

  loadAll: () => Promise<void>
  addReading: (r: PageReading) => void
  addInsight: (i: Insight) => void
  setActive: (v: boolean) => void
  setHasApiKey: (v: boolean) => void
  setSessionLabel: (v: string) => void
}

export const useResearchStore = create<ResearchState>((set, get) => ({
  readings: [],
  entities: [],
  insights: [],
  isActive: true,
  hasApiKey: false,
  sessionLabel: "Research Session",
  loading: false,

  loadAll: async () => {
    set({ loading: true })
    console.log("[Dashboard] 🔄 Loading all data from chrome.storage.local...")
    const [readings, entities, insights] = await Promise.all([
      getAllReadings(),
      getAllEntities(),
      getAllInsights()
    ])
    console.log("[Dashboard] 📊 Loaded:", {
      readings: readings.length,
      entities: entities.length,
      insights: insights.length
    })
    // Coerce date strings back to Date objects
    const fixedReadings = readings.map((r: any) => ({
      ...r,
      readAt: new Date(r.readAt),
      insights: (r.insights ?? []).map((i: any) => ({ ...i, createdAt: new Date(i.createdAt) }))
    }))
    const fixedInsights = insights.map((i: any) => ({ ...i, createdAt: new Date(i.createdAt) }))
    set({ readings: fixedReadings, entities, insights: fixedInsights, loading: false })
  },

  addReading: (reading) => {
    console.log("[Dashboard] ➕ Adding reading:", reading.title)
    set((s) => ({
      readings: [reading, ...s.readings],
      entities: mergeEntities(s.entities, reading.entities),
      insights: [...reading.insights, ...s.insights]
    }))
  },

  addInsight: (insight) => {
    set((s) => ({ insights: [insight, ...s.insights] }))
  },

  setActive: (v) => set({ isActive: v }),
  setHasApiKey: (v) => set({ hasApiKey: v }),
  setSessionLabel: (v) => set({ sessionLabel: v })
}))

function mergeEntities(existing: Entity[], incoming: Entity[]): Entity[] {
  const map = new Map(existing.map((e) => [e.name.toLowerCase(), e]))
  for (const e of incoming) {
    const key = e.name.toLowerCase()
    if (!map.has(key)) map.set(key, e)
    else {
      const ex = map.get(key)!
      map.set(key, {
        ...ex,
        seenOnPages: Array.from(new Set([...ex.seenOnPages, ...e.seenOnPages]))
      })
    }
  }
  return Array.from(map.values())
}
