"""
Observability — structured logging and pipeline tracing for ResearchMind.

Provides:
  - Structured JSON logs for every pipeline stage
  - Per-request trace with timing for each agent step
  - Summary metrics (pages processed, entities extracted, errors)
  - FastAPI middleware for request/response logging
"""
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ── Structured logger ─────────────────────────────────────────────────────────

class StructuredFormatter(logging.Formatter):
    """Emits log records as JSON lines for easy parsing/ingestion."""

    def format(self, record: logging.LogRecord) -> str:
        log = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if hasattr(record, "extra"):
            log.update(record.extra)
        if record.exc_info:
            log["exc"] = self.formatException(record.exc_info)
        return json.dumps(log)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


# ── Pipeline trace ────────────────────────────────────────────────────────────

@dataclass
class StageTrace:
    name: str
    started_at: float = field(default_factory=time.monotonic)
    ended_at: float | None = None
    status: str = "running"  # running | ok | error
    meta: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> float | None:
        if self.ended_at is None:
            return None
        return round((self.ended_at - self.started_at) * 1000, 1)

    def finish(self, status: str = "ok", **meta: Any) -> None:
        self.ended_at = time.monotonic()
        self.status = status
        self.meta.update(meta)


@dataclass
class PipelineTrace:
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    url: str = ""
    title: str = ""
    started_at: float = field(default_factory=time.monotonic)
    stages: list[StageTrace] = field(default_factory=list)
    _logger: logging.Logger = field(default_factory=lambda: get_logger("researchmind.trace"))

    def stage(self, name: str) -> StageTrace:
        s = StageTrace(name=name)
        self.stages.append(s)
        self._logger.info(
            f"[{self.trace_id}] → {name}",
            extra={"extra": {"trace_id": self.trace_id, "stage": name, "url": self.url}}
        )
        return s

    def finish(self, entities: int = 0, insights: int = 0, error: str | None = None) -> None:
        total_ms = round((time.monotonic() - self.started_at) * 1000, 1)
        summary = {
            "trace_id": self.trace_id,
            "url": self.url,
            "title": self.title[:60],
            "total_ms": total_ms,
            "stages": [
                {"name": s.name, "status": s.status, "ms": s.duration_ms, **s.meta}
                for s in self.stages
            ],
            "entities": entities,
            "insights": insights,
        }
        if error:
            summary["error"] = error
            self._logger.error(f"[{self.trace_id}] ✗ pipeline failed", extra={"extra": summary})
        else:
            self._logger.info(f"[{self.trace_id}] ✓ pipeline complete", extra={"extra": summary})


# ── Metrics (in-memory counters) ──────────────────────────────────────────────

class Metrics:
    def __init__(self) -> None:
        self.pages_processed = 0
        self.pages_skipped = 0
        self.pages_errored = 0
        self.total_entities = 0
        self.total_insights = 0
        self.total_ms = 0.0
        self._logger = get_logger("researchmind.metrics")

    def record_success(self, entities: int, insights: int, ms: float) -> None:
        self.pages_processed += 1
        self.total_entities += entities
        self.total_insights += insights
        self.total_ms += ms

    def record_skip(self, reason: str) -> None:
        self.pages_skipped += 1
        self._logger.info("page skipped", extra={"extra": {"reason": reason}})

    def record_error(self, error: str) -> None:
        self.pages_errored += 1
        self._logger.error("page error", extra={"extra": {"error": error}})

    def snapshot(self) -> dict:
        avg_ms = (self.total_ms / self.pages_processed) if self.pages_processed else 0
        return {
            "pages_processed": self.pages_processed,
            "pages_skipped": self.pages_skipped,
            "pages_errored": self.pages_errored,
            "total_entities": self.total_entities,
            "total_insights": self.total_insights,
            "avg_pipeline_ms": round(avg_ms, 1),
        }


# Global metrics instance
metrics = Metrics()


# ── FastAPI middleware ─────────────────────────────────────────────────────────

async def log_requests(request, call_next):
    """Middleware: log every request with method, path, status, and duration."""
    logger = get_logger("researchmind.http")
    start = time.monotonic()
    response = await call_next(request)
    ms = round((time.monotonic() - start) * 1000, 1)
    logger.info(
        f"{request.method} {request.url.path} → {response.status_code} ({ms}ms)",
        extra={"extra": {
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": ms,
        }}
    )
    return response
