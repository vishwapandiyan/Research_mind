export interface PageReading {
  id: string
  url: string
  title: string
  domain: string
  readAt: Date
  textContent: string
  headings: string[]
  summary: string
  entities: Entity[]
  insights: Insight[]
  readDepth: number
}

export interface Entity {
  id: string
  name: string
  type: "person" | "concept" | "claim" | "study" | "organization" | "date" | "place"
  description: string
  firstSeenAt: string
  seenOnPages: string[]
  relationships: Relationship[]
}

export interface Relationship {
  from: string
  to: string
  label: string
  sourcePages: string[]
  confidence: number
}

export interface Insight {
  id: string
  type: "discovery" | "contradiction" | "pattern" | "gap"
  text: string
  sourcePages: string[]
  relatedEntities: string[]
  createdAt: Date
}

export interface AgentMessage {
  role: "user" | "assistant"
  content: string
}

export interface PageExtractionEvent {
  type: "PAGE_EXTRACTED"
  payload: {
    url: string
    title: string
    textContent: string
    headings: string[]
    readDepth: number
  }
}

export interface DashboardUpdate {
  type: "READING_ADDED" | "INSIGHT_ADDED" | "ENTITY_UPDATED"
  payload: PageReading | Insight | Entity
}
