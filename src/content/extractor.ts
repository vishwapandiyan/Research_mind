import type { PlasmoCSConfig } from "plasmo"

export const config: PlasmoCSConfig = {
  matches: ["<all_urls>"],
  run_at: "document_idle"
}

const BLOCKLIST = [
  "mail.google.com", "outlook.live.com", "twitter.com", "x.com",
  "facebook.com", "instagram.com", "tiktok.com", "chase.com",
  "bankofamerica.com", "wellsfargo.com", "reddit.com"
]

const MIN_WORDS = 500
const DEBOUNCE_MS = 15000 // 15 seconds on page before extracting

function isDomainBlocked(hostname: string): boolean {
  return BLOCKLIST.some((d) => hostname.includes(d))
}

function extractText(): { text: string; headings: string[] } {
  // Clone body to avoid mutating the page
  const clone = document.body.cloneNode(true) as HTMLElement

  // Remove noise elements
  for (const tag of ["script", "style", "nav", "footer", "aside", "header", "noscript"]) {
    clone.querySelectorAll(tag).forEach((el) => el.remove())
  }

  // Prefer article/main content
  const content =
    clone.querySelector("article") ||
    clone.querySelector("main") ||
    clone.querySelector('[role="main"]') ||
    clone

  const text = (content.innerText || content.textContent || "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 32000) // ~8000 tokens

  const headings: string[] = []
  document.querySelectorAll("h1, h2, h3").forEach((h) => {
    const t = h.textContent?.trim()
    if (t) headings.push(t)
  })

  return { text, headings }
}

function wordCount(text: string): number {
  return text.split(/\s+/).filter(Boolean).length
}

let scrollDepth = 0
window.addEventListener("scroll", () => {
  const scrolled = window.scrollY + window.innerHeight
  const total = document.documentElement.scrollHeight
  scrollDepth = Math.max(scrollDepth, scrolled / total)
})

// Debounced extraction — only fires after user has been on page 15s
let timer: ReturnType<typeof setTimeout> | null = null

function scheduleExtraction() {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    const hostname = window.location.hostname
    if (isDomainBlocked(hostname)) return

    const { text, headings } = extractText()
    if (wordCount(text) < MIN_WORDS) return

    chrome.runtime.sendMessage({
      type: "PAGE_EXTRACTED",
      payload: {
        url: window.location.href,
        title: document.title,
        textContent: text,
        headings,
        readDepth: scrollDepth
      }
    })
  }, DEBOUNCE_MS)
}

// Trigger on load
scheduleExtraction()

// Re-trigger on SPA navigation
let lastUrl = location.href
new MutationObserver(() => {
  if (location.href !== lastUrl) {
    lastUrl = location.href
    scrollDepth = 0
    scheduleExtraction()
  }
}).observe(document, { subtree: true, childList: true })
