/**
 * ResearchMind Agent — thin client
 *
 * All heavy lifting (LangChain agents, MCP tool calls) happens in the
 * Python agent server at localhost:3738.
 *
 * This file calls the Python server directly and persists results locally.
 */

import { saveEntity, saveInsight, saveReading, getAllReadings } from "../shared/storage"
import type { Entity, Insight, PageReading } from "../shared/types"

const PYTHON = "http://localhost:3738"

export async function processPage(payload: {
  url: string
  title: string
  textContent: string
  headings: string[]
  readDepth: number
}): Promise<PageReading | null> {
  // Check Python agent server is up
  try {
    await fetch(`${PYTHON}/health`, { signal: AbortSignal.timeout(2000) })
  } catch {
    console.warn("[ResearchMind] Python agent not running. Start: python3 agents/server.py")
    return null
  }

  let reading: PageReading
  try {
    const res = await fetch(`${PYTHON}/process`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(120000)
    })
    if (!res.ok) throw new Error(`Agent returned ${res.status}`)
    const raw = await res.json()
    // Coerce date strings to Date objects
    reading = {
      ...raw,
      readAt: new Date(raw.readAt),
      insights: (raw.insights ?? []).map((i: any) => ({
        ...i,
        createdAt: new Date(i.createdAt)
      }))
    } as PageReading
  } catch (err) {
    console.error("[ResearchMind] Agent pipeline failed:", err)
    return null
  }

  // Persist locally — strip large textContent before saving
  const readingToSave: PageReading = {
    ...reading,
    textContent: "" // don't store full text, saves storage quota
  }
  try {
    console.log("[ResearchMind] 💾 Saving:", {
      title: reading.title,
      entities: readingToSave.entities?.length ?? 0,
      insights: readingToSave.insights?.length ?? 0
    })
    
    for (const entity of readingToSave.entities ?? []) {
      await saveEntity(entity as Entity)
    }
    for (const insight of readingToSave.insights ?? []) {
      await saveInsight(insight as Insight)
    }
    await saveReading(readingToSave)
    
    // Verify save
    const allReadings = await getAllReadings()
    console.log("[ResearchMind] ✅ Saved:", reading.title, `(Total readings: ${allReadings.length})`)
  } catch (err) {
    console.error("[ResearchMind] ❌ Save failed:", err)
  }

  return reading
}

export async function synthesizeSession(): Promise<string> {
  try {
    console.log("[ResearchMind] 🔄 Starting synthesis...")
    const res = await fetch(`${PYTHON}/synthesize`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
      signal: AbortSignal.timeout(120000)
    })
    if (!res.ok) {
      const error = await res.text()
      console.error("[ResearchMind] Synthesis error:", error)
      throw new Error(`Agent returned ${res.status}: ${error}`)
    }
    const data = await res.json()
    console.log("[ResearchMind] ✅ Synthesis complete")
    return data.summary ?? "No summary available."
  } catch (err) {
    console.error("[ResearchMind] ❌ Synthesis failed:", err)
    return `Synthesis failed: ${err}`
  }
}
