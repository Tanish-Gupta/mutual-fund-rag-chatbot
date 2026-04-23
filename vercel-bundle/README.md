# Index bundle for Vercel

The repo ships a **checked-in** lexical index so production works without Chroma on the server:

- **`index/5c4534f2-95a5-4a14-9402-3b2d424b99e3/chunks.jsonl`** — five Edelweiss scheme pages (merge build).  
- **`index_manifest.json` is omitted** here so Vercel uses **lexical-only** retrieval (`requirements-vercel.txt` stays small).

`scripts/vercel_build.sh` copies `vercel-bundle/index/*` → `data/index/` on each Vercel build.

### Refreshing the bundle

After you run `mf-pipeline` (or `scripts/rebuild_five_funds_index.py`) locally:

```bash
INGEST_RUN_ID="<new-uuid>"
mkdir -p "vercel-bundle/index/$INGEST_RUN_ID"
cp "data/index/$INGEST_RUN_ID/chunks.jsonl" "vercel-bundle/index/$INGEST_RUN_ID/"
git add "vercel-bundle/index/$INGEST_RUN_ID/chunks.jsonl"
# Optionally remove the old run directory under vercel-bundle/index/ to avoid shipping two copies.
```

### Full vector search on Vercel

Copy **`index_manifest.json`** only if you add Pinecone + embedding deps and env vars — see **[docs/VERCEL.md](../docs/VERCEL.md)**.
