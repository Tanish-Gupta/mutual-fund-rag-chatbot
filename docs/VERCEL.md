# Deploy on Vercel

The repo is wired for **[Vercel](https://vercel.com/)** using the official **FastAPI + `main.py`** pattern: one serverless function serves `/health`, `/api/index-meta`, and `/api/chat`; static files come from **`public/`** (filled by `scripts/vercel_build.sh` from `phase4/web/`).

## What gets deployed

| Piece | How |
|--------|-----|
| **API** | Root [`main.py`](../main.py) adds `phase*/src` to `PYTHONPATH` and re-exports `mf_chat.app:app`. |
| **UI** | Build copies `phase4/web/*` → `public/` and `chat.html` → `public/index.html` (chat at `/`). |
| **Index** | Optional: put `vercel-bundle/index/<ingest_run_id>/chunks.jsonl` in git (see [vercel-bundle/README.md](../vercel-bundle/README.md)). Build copies into `data/index/`. |

## Lexical-only (recommended first deploy)

1. Run `mf-pipeline` (or your merge script) locally so you have `data/index/<run_id>/chunks.jsonl`.
2. Copy that file into `vercel-bundle/index/<run_id>/` (same layout as under `data/index/`).
3. **Do not** copy `index_manifest.json` if you want **lexical-only** retrieval (no `sentence-transformers` / Chroma / Pinecone on Vercel — smaller cold starts). The chat service falls back to `retrieve()` over the JSONL when no manifest is present.
4. Connect the GitHub repo in Vercel; use defaults plus env vars below.

## Environment variables (Vercel → Project → Settings → Environment Variables)

| Variable | Required | Purpose |
|----------|----------|---------|
| `GROQ_API_KEY` | Optional | Natural answers; omit for excerpt-only fallback. |
| `GROQ_MODEL` | Optional | Override default Groq model id. |
| `PINECONE_API_KEY` | Only with manifest | Vector query to Pinecone. |
| `PINECONE_INDEX` | Only with manifest | Index name in manifest / env. |
| `HF_TOKEN` | Optional | Hugging Face Hub when using embedding models in CI or if you add `sentence-transformers` on Vercel. |

If you ship **`index_manifest.json`** with `"backend": "pinecone"`, add **`pinecone-client`** (and **`sentence-transformers`** for query embeddings) to `requirements-vercel.txt` and set Pinecone secrets — see `mf_index/retrieval.py`.

## Limits

- [Vercel Functions limits](https://vercel.com/docs/functions/limitations) (timeout, bundle size) apply. Chroma’s on-disk DB is **not** used on Vercel; use **Pinecone** + manifest if you need dense retrieval in the cloud.
- `public/` is produced at build time; it is **gitignored** in this repo to avoid committing build output locally (Vercel still runs the build on each deploy).

## Local check (optional)

Use the [Vercel CLI](https://vercel.com/docs/cli) from the repo root (`vercel dev`) for the closest match to production routing. For API-only local runs, continue using `uvicorn mf_chat.app:app` as in the main README.
