/**
 * Storage — uses chrome.storage.local (works in MV3 service workers).
 * All data is stored in chrome.storage.local, NOT IndexedDB.
 */
import type { Entity, Insight, PageReading, Relationship } from "./types"

// ── chrome.storage.local helpers ─────────────────────────────────────────────

async function storageGet<T>(key: string): Promise<T | null> {
  return new Promise((resolve) => {
    chrome.storage.local.get(key, (result) => {
      resolve(result[key] ?? null)
    })
  })
}

async function storageSet(key: string, value: unknown): Promise<void> {
  return new Promise((resolve) => {
    chrome.storage.local.set({ [key]: value }, resolve)
  })
}

// ── Readings ──────────────────────────────────────────────────────────────────

export async function saveReading(reading: PageReading): Promise<void> {
  const all = (await storageGet<PageReading[]>("readings")) ?? []
  const filtered = all.filter((r) => r.id !== reading.id)
  await storageSet("readings", [reading, ...filtered].slice(0, 200))
}

export async function getAllReadings(): Promise<PageReading[]> {
  return (await storageGet<PageReading[]>("readings")) ?? []
}

// ── Entities ──────────────────────────────────────────────────────────────────

export async function saveEntity(entity: Entity): Promise<Entity> {
  const all = (await storageGet<Entity[]>("entities")) ?? []
  const existingIdx = all.findIndex(
    (e) => e.name.toLowerCase() === entity.name.toLowerCase()
  )
  if (existingIdx >= 0) {
    const existing = all[existingIdx]
    const merged: Entity = {
      ...existing,
      seenOnPages: Array.from(new Set([...existing.seenOnPages, ...entity.seenOnPages])),
      relationships: mergeRelationships(existing.relationships, entity.relationships)
    }
    all[existingIdx] = merged
    await storageSet("entities", all)
    return merged
  }
  await storageSet("entities", [...all, entity])
  return entity
}

export async function getAllEntities(): Promise<Entity[]> {
  return (await storageGet<Entity[]>("entities")) ?? []
}

// ── Insights ──────────────────────────────────────────────────────────────────

export async function saveInsight(insight: Insight): Promise<void> {
  const all = (await storageGet<Insight[]>("insights")) ?? []
  await storageSet("insights", [insight, ...all].slice(0, 500))
}

export async function getAllInsights(): Promise<Insight[]> {
  return (await storageGet<Insight[]>("insights")) ?? []
}

// ── Clear ─────────────────────────────────────────────────────────────────────

export async function clearAll(): Promise<void> {
  await storageSet("readings", [])
  await storageSet("entities", [])
  await storageSet("insights", [])
}

// ── Debug ─────────────────────────────────────────────────────────────────────

export async function debugStorage(): Promise<void> {
  const readings = await getAllReadings()
  const entities = await getAllEntities()
  const insights = await getAllInsights()
  console.log("[Storage Debug]", {
    readings: readings.length,
    entities: entities.length,
    insights: insights.length,
    sampleReading: readings[0],
    sampleEntity: entities[0],
    sampleInsight: insights[0]
  })
}

// Make it available globally for console debugging
if (typeof globalThis !== "undefined") {
  ;(globalThis as any).__RM_DEBUG_STORAGE__ = debugStorage
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function mergeRelationships(existing: Relationship[], incoming: Relationship[]): Relationship[] {
  const map = new Map<string, Relationship>()
  for (const r of existing) map.set(`${r.from}::${r.to}::${r.label}`, r)
  for (const r of incoming) {
    const key = `${r.from}::${r.to}::${r.label}`
    if (!map.has(key)) map.set(key, r)
    else {
      const ex = map.get(key)!
      map.set(key, {
        ...ex,
        sourcePages: Array.from(new Set([...ex.sourcePages, ...r.sourcePages])),
        confidence: Math.max(ex.confidence, r.confidence)
      })
    }
  }
  return Array.from(map.values())
}
