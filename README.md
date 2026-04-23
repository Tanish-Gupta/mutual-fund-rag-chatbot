# Mutual fund RAG chatbot (FundFacts)

Facts-only Q&A over **indexed** mutual fund scheme pages (IndMoney and similar). Answers are grounded in your local vector index; **Groq** optionally rewrites replies in a natural tone. The product does **not** give investment advice, buy/sell recommendations, or personal portfolio guidance.

**Live docs in repo:** [RAG architecture](docs/RAG_ARCHITECTURE.md) · [Data schema](docs/DATA_SCHEMA.md) · [Daily scheduler](docs/SCHEDULER.md) · [Vercel deploy](docs/VERCEL.md)

## Features

| Phase | What it does |
|-------|----------------|
| **1 — Ingest** | Fetch allowlisted URLs, store raw HTML, optional structured JSON |
| **2 — Index** | Chunk → embed (`sentence-transformers`) → **Chroma** (default) or **Pinecone** |
| **3 — API** | FastAPI `POST /api/chat`, `GET /api/index-meta`, `GET /health` |
| **4 — UI** | Static `phase4/web/chat.html` (full-width chat, quick prompts, sources) |
| **5 — Pipeline** | `mf-pipeline` = ingest then index; optional **launchd/cron** at 10:00 local; **GitHub Actions** at 10:00 IST |

## Requirements

- **Python 3.10+** (3.9 may work for some paths; `pyproject.toml` targets 3.10+)
- **Network** for ingest and Groq
- Optional: **Playwright** if sites return Cloudflare to plain HTTP (`pip install -e ".[browser]"` + `playwright install chromium`)

## Quick start

```bash
git clone https://github.com/Tanish-Gupta/mutual-fund-rag-chatbot.git
cd mutual-fund-rag-chatbot

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[vector]"

cp .env.example .env
# Set GROQ_API_KEY (optional but recommended for natural answers)
# Set PINECONE_* only if you use --backend pinecone
```

### Environment (`/.env`)

| Variable | Purpose |
|----------|---------|
| `GROQ_API_KEY` | Optional; enables Groq for grounded answers |
| `GROQ_MODEL` | Optional model id (default in code) |
| `PINECONE_API_KEY` / `PINECONE_INDEX` | Only for Pinecone backend |

Never commit `.env` (it is gitignored).

### One-shot ingest + index

```bash
export PYTHONPATH="phase1/src:phase2/src:phase3/src:phase5/src"
python3 -m mf_pipeline --index-backend chroma
# If fetch fails: add --browser (after installing optional browser deps)
```

### Run API + UI locally

```bash
export PYTHONPATH="phase1/src:phase2/src:phase3/src:phase5/src"
python3 -m uvicorn mf_chat.app:app --host 127.0.0.1 --port 8000
```

```bash
cd phase4/web && python3 -m http.server 8080 --bind 127.0.0.1
```

Open **http://127.0.0.1:8080/chat.html** — the UI defaults API base to `http://127.0.0.1:8000` on localhost. The header shows **index last updated** from `GET /api/index-meta`.

### Deploy on Vercel (API + static UI)

See **[docs/VERCEL.md](docs/VERCEL.md)**. Summary: connect the repo in Vercel; build uses `vercel.json` + `scripts/vercel_build.sh`; ASGI entry is **`api/index.py`**. Add optional **`vercel-bundle/index/<ingest_run_id>/chunks.jsonl`** for lexical Q&A without Chroma on the server.

### Seed URLs

Default IndMoney scheme URLs live in `phase1/src/mf_ingest/config.py` (`DEFAULT_SEED_URLS`). Edit or pass extra `--url` flags to `mf-ingest` / `mf-pipeline`.

## CLI entrypoints

After `pip install -e ".[vector]"`:

| Command | Role |
|---------|------|
| `mf-ingest run` | Phase 1 fetch + parse |
| `mf-index build --run-id <uuid>` | Phase 2 index |
| `mf-pipeline` | Phase 1 + 2 |
| `mf-chat` | Dev server (uvicorn :8000) |

If editable install fails on older pip, use `PYTHONPATH` as in the snippets above.

## Tests

```bash
pip install pytest
export PYTHONPATH="phase1/src:phase2/src:phase3/src:phase5/src"
pytest tests/ -q
```

## Scheduler

To rebuild the index **every day at 10:00** (local time for launchd/cron, IST for GitHub Actions), see **[docs/SCHEDULER.md](docs/SCHEDULER.md)** (`scripts/run_daily_pipeline.sh`, launchd / cron, Actions).

## Compliance & safety

- Answers are intended to come **only** from retrieved chunks; refusals for advice, buy/sell, and personal data are routed in code.
- Educational links on refusals include **AMFI** and **SEBI investor** resources.
- You are responsible for **robots.txt**, site terms, and API keys on your deployment.

## License

No license file is bundled by default; add one if you open-source formally.

---

**Repository:** [github.com/Tanish-Gupta/mutual-fund-rag-chatbot](https://github.com/Tanish-Gupta/mutual-fund-rag-chatbot)
