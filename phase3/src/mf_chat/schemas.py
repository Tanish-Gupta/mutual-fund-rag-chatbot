from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    ingest_run_id: str | None = Field(
        default=None,
        description="Use this ingest run's index; default = latest under data/index/",
    )


class SourceRef(BaseModel):
    """One canonical page URL that contributed retrieved text."""

    url: str
    scheme_name: str | None = None


class IndexMetaResponse(BaseModel):
    """Latest vector index metadata for the UI."""

    ingest_run_id: str | None = Field(
        default=None,
        description="Active default index run under data/index/",
    )
    last_updated_iso: str | None = Field(
        default=None,
        description="When index_manifest.json or chunks.jsonl was last written (ISO-8601 UTC)",
    )


class ChatResponse(BaseModel):
    answer: str
    source_urls: list[str] = Field(
        ...,
        description="Allowlisted page URLs the answer was derived from (deduplicated, order preserved by relevance)",
    )
    sources: list[SourceRef] = Field(
        default_factory=list,
        description="Same URLs with optional scheme labels for UI",
    )
    ingest_run_id: str
