import { processPage } from "./agent"

interface QueueItem {
  url: string
  title: string
  textContent: string
  headings: string[]
  readDepth: number
}

const queue: QueueItem[] = []
let processing = false
const BATCH_SIZE = 3 // process up to 3 pages concurrently

export function enqueue(item: QueueItem) {
  if (queue.some((q) => q.url === item.url)) return
  queue.push(item)
  if (!processing) drain()
}

async function broadcastToDashboard(message: object) {
  console.log("[Queue] 📡 Broadcasting to dashboard:", message)
  const tabs = await chrome.tabs.query({ url: chrome.runtime.getURL("tabs/dashboard.html") })
  console.log("[Queue] Found dashboard tabs:", tabs.length)
  for (const tab of tabs) {
    if (tab.id) chrome.tabs.sendMessage(tab.id, message).catch(() => {})
  }
  chrome.runtime.sendMessage(message).catch(() => {})
}

async function drain() {
  if (processing || queue.length === 0) return
  processing = true

  while (queue.length > 0) {
    // Take up to BATCH_SIZE items and process concurrently
    const batch = queue.splice(0, BATCH_SIZE)
    const results = await Promise.allSettled(batch.map((item) => processPage(item)))

    for (const result of results) {
      if (result.status === "fulfilled" && result.value) {
        await broadcastToDashboard({ type: "READING_ADDED", payload: result.value })
      }
    }
  }

  processing = false
}
