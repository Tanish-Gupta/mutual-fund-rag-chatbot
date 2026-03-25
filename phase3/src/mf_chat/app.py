from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mf_chat.paths import latest_index_last_modified_utc
from mf_chat.schemas import ChatRequest, ChatResponse, IndexMetaResponse
from mf_chat.service import chat

app = FastAPI(title="MF RAG Chat (Phase 3)", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/index-meta", response_model=IndexMetaResponse)
def get_index_meta() -> IndexMetaResponse:
    rid, iso = latest_index_last_modified_utc()
    return IndexMetaResponse(ingest_run_id=rid, last_updated_iso=iso)


@app.post("/api/chat", response_model=ChatResponse)
def post_chat(body: ChatRequest) -> ChatResponse:
    return chat(body.message.strip(), body.ingest_run_id)
