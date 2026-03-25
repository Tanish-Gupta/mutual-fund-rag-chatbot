from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FetchOutcome(str, Enum):
    FETCHED = "fetched"
    UNCHANGED = "unchanged"
    SKIPPED = "skipped"
    ERROR = "error"
    CLOUDFLARE_CHALLENGE = "cloudflare_challenge"


class SourceRecord(BaseModel):
    source_url: str
    slug: str
    outcome: FetchOutcome
    http_status: int | None = None
    content_hash: str | None = None
    raw_relative_path: str | None = None
    byte_size: int | None = None
    error_message: str | None = None
    notes: str | None = None


class IngestManifest(BaseModel):
    ingest_run_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    trigger: str = "manual"
    status: str = "running"
    sources: list[SourceRecord] = Field(default_factory=list)
    pipeline_phase: str = "ingest"


class SchemePageStructured(BaseModel):
    """Structured facts extracted from an IndMoney-style scheme page (best-effort)."""

    source_url: str
    scheme_name: str | None = None
    snapshot: dict[str, str | None] = Field(default_factory=dict)
    sections: dict[str, str] = Field(default_factory=dict)
    fund_managers: list[dict[str, str | None]] = Field(default_factory=list)
    performance_table: dict[str, Any] | None = Field(
        default=None,
        description="Fund vs benchmark vs category returns by period (from fund_performance API)",
    )
    next_data_snippet: dict[str, Any] | None = Field(
        default=None,
        description="Subset of __NEXT_DATA__ if present, for debugging / future mappers",
    )
