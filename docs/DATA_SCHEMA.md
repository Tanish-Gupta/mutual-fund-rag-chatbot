# Data schema — Mutual Fund facts-only RAG chatbot

This document defines logical entities, fields, and relationships for ingestion, indexing, chat runtime, and pipeline jobs. Implementations may map these to SQL (e.g. PostgreSQL + pgvector), JSON documents, or object storage keys consistently.

---

## 1. Entity relationship overview

```
Scheme ──< SchemeAlias
Scheme ──< DocumentArtifact ──< DocumentVersion ──< Chunk
IngestRun ──< IngestRunSource
Conversation ──< Message
Chunk (vector index row references chunk_id)
```

---

## 2. Core tables / collections

### 2.1 `schemes`

Canonical registry for mutual fund schemes referenced by the bot.

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `scheme_id` | UUID / string | yes | Primary key; stable internal ID |
| `amfi_scheme_code` | string | no | AMFI scheme code when known |
| `isin` | string | no | ISIN for the plan/option if applicable |
| `fund_name` | string | yes | Display / official name |
| `amc_id` | string | yes | Foreign key to AMC |
| `plan` | enum | yes | `direct` \| `regular` |
| `option` | enum | yes | `growth` \| `idcw` \| `idcw_reinvest` etc. |
| `category` | string | no | AMFI category label |
| `seed_source_urls` | string[] | no | Initial discovery URLs (e.g. indmoney pages) |
| `created_at` | datetime | yes | |
| `updated_at` | datetime | yes | |

**Indexes:** `amfi_scheme_code`, `isin`, `fund_name` (trigram or full-text for resolution).

---

### 2.2 `scheme_aliases`

Maps alternate names / typos / short names to `scheme_id`.

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `alias_id` | UUID | yes | PK |
| `scheme_id` | FK → schemes | yes | |
| `alias_text` | string | yes | Normalized lowercase for matching |
| `source` | string | no | `manual`, `amfi_import`, `llm_suggested` |

---

### 2.3 `amcs`

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `amc_id` | string | yes | PK (slug or AMFI AMC code) |
| `name` | string | yes | |
| `base_url` | string | no | Official site root for allowlisting |
| `created_at` | datetime | yes | |

---

### 2.4 `document_artifacts`

Logical document (e.g. “KIM for scheme X”), not each fetch.

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `artifact_id` | UUID | yes | PK |
| `scheme_id` | FK | no | Null for global docs (SEBI, AMFI master) |
| `doc_type` | enum | yes | See §5 |
| `title` | string | no | |
| `canonical_url` | string | yes | **Single URL shown to users** when this doc is cited |
| `alternate_urls` | string[] | no | Mirrors, CDN; not for user display |
| `primary_source_domain` | string | yes | For allowlist checks |
| `created_at` | datetime | yes | |
| `updated_at` | datetime | yes | |

---

### 2.5 `document_versions`

Immutable snapshot per fetch/processing run.

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `version_id` | UUID | yes | PK |
| `artifact_id` | FK | yes | |
| `ingest_run_id` | FK | yes | |
| `fetched_at` | datetime | yes | |
| `content_hash` | string | yes | SHA-256 of normalized raw bytes |
| `mime_type` | string | yes | `text/html`, `application/pdf`, … |
| `raw_storage_uri` | string | yes | `s3://…` / `file://…` pointer to blob |
| `byte_size` | int | yes | |
| `parser_status` | enum | yes | `pending` \| `parsed` \| `failed` |
| `effective_date` | date | no | From document (“as on …”) |
| `metadata_json` | JSON | no | Extra headers, PDF page count, etc. |

**Constraint:** at most one `version_id` marked `is_active` per `artifact_id` for retrieval (optional `is_active` boolean).

---

### 2.6 `chunks`

Retrieval unit stored in vector DB + optional relational mirror.

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `chunk_id` | UUID | yes | PK; same id in vector index |
| `version_id` | FK | yes | |
| `artifact_id` | FK | yes | Denormalized for filtering |
| `scheme_id` | FK | no | Denormalized; set when chunk is scheme-specific |
| `doc_type` | enum | yes | Copy for filter |
| `text` | text | yes | Chunk plain text |
| `token_count` | int | no | |
| `chunk_index` | int | yes | Order within version |
| `section_heading` | string | no | Parsed heading breadcrumb |
| `canonical_url` | string | yes | Denormalized from artifact for citation |
| `as_of_date` | date | no | Propagated from version / table caption |
| `fact_keys` | string[] | no | Optional tags: `expense_ratio`, `exit_load`, … |
| `embedding_model_id` | string | no | Model name + version used |
| `created_at` | datetime | yes | |

**Vector store:** store `chunk_id` + embedding vector + optional sparse vector / BM25 external id.

---

### 2.7 `ingest_runs`

One scheduler or manual pipeline execution.

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `ingest_run_id` | UUID | yes | PK |
| `trigger` | enum | yes | `scheduler` \| `manual` \| `webhook` |
| `started_at` | datetime | yes | |
| `finished_at` | datetime | no | |
| `status` | enum | yes | `running` \| `success` \| `partial` \| `failed` |
| `pipeline_phases` | JSON | no | Per-phase status timestamps (see architecture doc) |
| `error_summary` | text | no | |

---

### 2.8 `ingest_run_sources`

Per-URL or per-source outcome within a run.

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `id` | UUID | yes | PK |
| `ingest_run_id` | FK | yes | |
| `source_url` | string | yes | |
| `artifact_id` | FK | no | Created or updated artifact |
| `http_status` | int | no | |
| `outcome` | enum | yes | `fetched` \| `unchanged` \| `skipped` \| `error` |
| `error_message` | text | no | |

---

### 2.9 `conversations`

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `conversation_id` | UUID | yes | PK |
| `user_id` | string | no | If auth exists |
| `created_at` | datetime | yes | |
| `updated_at` | datetime | yes | |
| `metadata_json` | JSON | no | Client locale, channel |

---

### 2.10 `messages`

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `message_id` | UUID | yes | PK |
| `conversation_id` | FK | yes | |
| `role` | enum | yes | `user` \| `assistant` \| `system` |
| `content` | text | yes | User text or assistant reply |
| `source_url` | string | no | **Exactly one** for assistant factual replies (validated) |
| `retrieved_chunk_ids` | UUID[] | no | Audit trail |
| `intent` | string | no | Router output, e.g. `FACT_SCHEME` |
| `refusal_reason` | string | no | If response was facts-only refusal |
| `model_id` | string | no | e.g. Groq model id |
| `created_at` | datetime | yes | |

---

### 2.11 `pipeline_jobs` (optional queue)

For async phase execution after scheduler fires.

| Field | Type | Required | Description |
|--------|------|----------|-------------|
| `job_id` | UUID | yes | PK |
| `ingest_run_id` | FK | yes | |
| `phase` | enum | yes | `ingest` \| `process` \| `index` |
| `status` | enum | yes | `queued` \| `running` \| `done` \| `failed` |
| `payload_json` | JSON | no | |
| `started_at` / `finished_at` | datetime | no | |

---

## 3. Enums reference

### `doc_type` (extend as needed)

- `scheme_page` — third-party or AMC HTML detail pages  
- `factsheet`  
- `kim` — Key Information Memorandum  
- `sid` — Scheme Information Document  
- `amfi_master` — AMFI scheme master / industry data  
- `sebi_circular` — guidelines (riskometer, disclosures)  
- `rta_guide` — CAMS / KFintech help articles  
- `amc_investor_faq`  

---

## 4. Vector index record (logical)

Minimal fields stored alongside embeddings:

| Field | Description |
|--------|-------------|
| `chunk_id` | Join key to `chunks` |
| `embedding` | float[] |
| `scheme_id` | Filter |
| `doc_type` | Filter |
| `canonical_url` | Fast citation without extra join |

---

## 5. API DTOs (suggested)

### Chat request

```json
{
  "conversation_id": "uuid optional",
  "message": "string",
  "locale": "en-IN optional"
}
```

### Chat response

```json
{
  "conversation_id": "uuid",
  "message_id": "uuid",
  "answer": "string",
  "source_url": "string",
  "intent": "FACT_SCHEME",
  "scheme_id": "uuid optional"
}
```

### Refusal response (same shape; `intent` e.g. `REFUSE_ADVICE`)

```json
{
  "answer": "string",
  "source_url": "string",
  "intent": "REFUSE_ADVICE"
}
```

---

## 6. Groq / LLM audit fields

Store on `messages` or a child `llm_calls` table if you need fine-grained cost and debugging:

| Field | Description |
|--------|-------------|
| `provider` | `groq` |
| `model` | e.g. `llama-3.3-70b-versatile` |
| `prompt_tokens` / `completion_tokens` | |
| `latency_ms` | |

---

## 7. Versioning rules

1. **New `content_hash`** for an artifact → new `document_versions` row → re-chunk → replace or supersede chunks in index for that `artifact_id`.  
2. **Canonical URL** changes rarely; if it changes, update `document_artifacts.canonical_url` and propagate to new chunks only.  
3. **Scheme merge/split** — update `scheme_id` on artifacts/chunks via admin migration.

---

*Last updated: aligns with `RAG_ARCHITECTURE.md` five-phase model.*
