"""
Guardrails — input validation, output schema enforcement, and safety constraints.

Applied at two points:
  1. Before processing: validate page payload (input guardrails)
  2. After extraction: validate and sanitize LLM output (output guardrails)
"""
import re
from typing import Any

# ── Input guardrails ──────────────────────────────────────────────────────────

# Domains that should never be processed (privacy-sensitive)
BLOCKED_DOMAINS = {
    "mail.google.com", "outlook.live.com", "outlook.office.com",
    "bank", "chase.com", "wellsfargo.com", "paypal.com",
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "tiktok.com", "snapchat.com",
    "accounts.google.com", "login.", "signin.", "auth.",
}

MIN_WORD_COUNT = 100  # pages shorter than this are skipped
MAX_TEXT_LENGTH = 8000  # cap input to agents


class InputValidationError(Exception):
    pass


def validate_page(payload: dict) -> dict:
    """
    Validate and sanitize a page payload before sending to agents.
    Raises InputValidationError if the page should be skipped.
    Returns a sanitized copy of the payload.
    """
    url = payload.get("url", "")
    title = payload.get("title", "")
    text = payload.get("textContent", "")

    # Block sensitive domains
    domain = _extract_domain(url)
    for blocked in BLOCKED_DOMAINS:
        if blocked in domain:
            raise InputValidationError(f"Blocked domain: {domain}")

    # Skip pages with too little content
    word_count = len(text.split())
    if word_count < MIN_WORD_COUNT:
        raise InputValidationError(
            f"Page too short ({word_count} words, minimum {MIN_WORD_COUNT})"
        )

    # Sanitize: strip any injected prompt-like content
    text = _strip_prompt_injection(text)

    # Cap text length
    text = text[:MAX_TEXT_LENGTH]

    return {**payload, "textContent": text}


def _extract_domain(url: str) -> str:
    try:
        return url.split("/")[2].lower()
    except IndexError:
        return url.lower()


def _strip_prompt_injection(text: str) -> str:
    """Remove common prompt injection patterns from page content."""
    patterns = [
        r"ignore (all |previous |prior )?instructions",
        r"you are now",
        r"new system prompt",
        r"disregard (all |your )?previous",
        r"forget (everything|all instructions)",
    ]
    for pattern in patterns:
        text = re.sub(pattern, "[removed]", text, flags=re.IGNORECASE)
    return text


# ── Output guardrails ─────────────────────────────────────────────────────────

MAX_ENTITIES = 10
MAX_RELATIONSHIPS = 8
MAX_INSIGHTS = 6
MAX_TEXT_FIELD = 500  # max chars per text field in output

VALID_ENTITY_TYPES = {
    "person", "concept", "claim", "study", "organization", "date", "place"
}
VALID_INSIGHT_TYPES = {"discovery", "contradiction", "pattern", "gap"}


def validate_extraction(result: dict) -> dict:
    """
    Validate and sanitize LLM extraction output.
    Enforces schema, caps list sizes, sanitizes text fields.
    Returns a clean, safe result dict.
    """
    return {
        "summary": _safe_str(result.get("summary", ""), MAX_TEXT_FIELD),
        "entities": _validate_entities(result.get("entities", [])),
        "relationships": _validate_relationships(result.get("relationships", [])),
        "insights": _validate_insights(result.get("insights", [])),
        "prior_context_used": bool(result.get("prior_context_used", False)),
    }


def _validate_entities(entities: Any) -> list:
    if not isinstance(entities, list):
        return []
    valid = []
    for e in entities[:MAX_ENTITIES]:
        if not isinstance(e, dict) or not e.get("name"):
            continue
        entity_type = e.get("type", "concept")
        if entity_type not in VALID_ENTITY_TYPES:
            entity_type = "concept"
        valid.append({
            "name": _safe_str(e["name"], 100),
            "type": entity_type,
            "description": _safe_str(e.get("description", ""), MAX_TEXT_FIELD),
        })
    return valid


def _validate_relationships(relationships: Any) -> list:
    if not isinstance(relationships, list):
        return []
    valid = []
    for r in relationships[:MAX_RELATIONSHIPS]:
        if not isinstance(r, dict):
            continue
        if not r.get("from") or not r.get("to"):
            continue
        confidence = r.get("confidence", 0.5)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        confidence = max(0.0, min(1.0, float(confidence)))
        valid.append({
            "from": _safe_str(r["from"], 100),
            "to": _safe_str(r["to"], 100),
            "label": _safe_str(r.get("label", "related"), 100),
            "confidence": confidence,
        })
    return valid


def _validate_insights(insights: Any) -> list:
    if not isinstance(insights, list):
        return []
    valid = []
    for i in insights[:MAX_INSIGHTS]:
        if not isinstance(i, dict) or not i.get("text"):
            continue
        insight_type = i.get("type", "discovery")
        if insight_type not in VALID_INSIGHT_TYPES:
            insight_type = "discovery"
        valid.append({
            "type": insight_type,
            "text": _safe_str(i["text"], MAX_TEXT_FIELD),
        })
    return valid


def _safe_str(value: Any, max_len: int) -> str:
    if not isinstance(value, str):
        value = str(value) if value is not None else ""
    return value[:max_len].strip()
