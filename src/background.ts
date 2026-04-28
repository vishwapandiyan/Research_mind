import { synthesizeSession } from "./background/agent"
import { enqueue } from "./background/queue"

// Restore persisted config on startup
chrome.storage.local.get(["provider", "apiKey", "ollamaModel", "active"], (result) => {
  const g = globalThis as any
  g.__RM_PROVIDER__ = result.provider ?? "ollama"
  g.__RM_API_KEY__ = result.apiKey ?? ""
  g.__RM_OLLAMA_MODEL__ = result.ollamaModel ?? "qwen3:8b"
  g.__RM_ACTIVE__ = result.active ?? true
})

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  const g = globalThis as any

  switch (message.type) {
    case "PAGE_EXTRACTED": {
      if (!(g.__RM_ACTIVE__ ?? true)) return
      enqueue(message.payload)
      sendResponse({ ok: true })
      break
    }

    case "SET_CONFIG": {
      // { provider, apiKey?, ollamaModel? }
      if (message.provider) g.__RM_PROVIDER__ = message.provider
      if (message.apiKey !== undefined) g.__RM_API_KEY__ = message.apiKey
      if (message.ollamaModel) g.__RM_OLLAMA_MODEL__ = message.ollamaModel
      chrome.storage.local.set({
        provider: g.__RM_PROVIDER__,
        apiKey: g.__RM_API_KEY__,
        ollamaModel: g.__RM_OLLAMA_MODEL__
      })
      sendResponse({ ok: true })
      break
    }

    case "SET_ACTIVE": {
      g.__RM_ACTIVE__ = message.active
      chrome.storage.local.set({ active: message.active })
      sendResponse({ ok: true })
      break
    }

    case "SYNTHESIZE": {
      synthesizeSession().then((summary) => sendResponse({ summary }))
      return true
    }

    case "GET_STATE": {
      sendResponse({
        active: g.__RM_ACTIVE__ ?? true,
        provider: g.__RM_PROVIDER__ ?? "ollama",
        ollamaModel: g.__RM_OLLAMA_MODEL__ ?? "qwen3:8b",
        hasApiKey: !!(g.__RM_API_KEY__)
      })
      break
    }
  }

  return true
})
