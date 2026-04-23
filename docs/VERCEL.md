# Deploy on Vercel

The repo is wired for **[Vercel](https://vercel.com/)** using the **FastAPI** Python runtime with **`api/index.py`** (Vercel only matches `functions` config against files under `api/`). One serverless function serves `/health`, `/api/index-meta`, and `/api/chat`; static files come from **`public/`** (filled by `scripts/vercel_build.sh` from `phase4/web/`).

## What gets deployed

| Piece | How |
|--------|-----|
| **API** | [`api/index.py`](../api/index.py) (required by Vercel’s `api/` layout) adds `phase*/src` to `PYTHONPATH` and re-exports `mf_chat.app:app`. |
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

## Build shows `externally-managed-environment` (pip)

Vercel’s build Python is managed by **`uv`**. A custom **`pip install -r …`** hits PEP 668 and fails. This repo uses **`uv pip install -r requirements-vercel.txt`** in `vercel.json` instead.

## Build shows `main.py` / `functions` error

That message only appears when Vercel is building an **older commit** (before `api/index.py` existed), or when **Project Settings** override `vercel.json`:

1. In GitHub, confirm **`main`** includes commit **`0c1a253`** or newer (search the repo’s commit history for “move ASGI entry to api”).
2. In Vercel → **Deployments** → open the failed deploy and check **Source** → **Commit**. It must **not** be `d3cdc66`. Use **Redeploy** on the latest deployment, or **Deployments → … → Redeploy** after pushing.
3. Vercel → **Project → Settings → General / Build & Development**: remove any custom **Install Command** / **Build Command** / **Root Directory** that point at an old fork or branch, unless you intend them.

## Limits

- [Vercel Functions limits](https://vercel.com/docs/functions/limitations) (timeout, bundle size) apply. Chroma’s on-disk DB is **not** used on Vercel; use **Pinecone** + manifest if you need dense retrieval in the cloud.
- `public/` is produced at build time; it is **gitignored** in this repo to avoid committing build output locally (Vercel still runs the build on each deploy).

## Local check (optional)

Use the [Vercel CLI](https://vercel.com/docs/cli) from the repo root (`vercel dev`) for the closest match to production routing. For API-only local runs, continue using `uvicorn mf_chat.app:app` as in the main README.
