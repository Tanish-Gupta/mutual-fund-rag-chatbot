# Index bundle for Vercel (optional)

To answer questions in production, the API needs **`chunks.jsonl`** (and optionally **`index_manifest.json`**) under `data/index/<ingest_run_id>/`.

For Vercel, copy that folder **here** before deploy so `scripts/vercel_build.sh` can copy it into `data/index/` during the Vercel build (the normal `data/index/` path is gitignored).

Example (from your machine, after `mf-pipeline`):

```bash
INGEST_RUN_ID="<your-uuid>"
mkdir -p "vercel-bundle/index/$INGEST_RUN_ID"
cp "data/index/$INGEST_RUN_ID/chunks.jsonl" "vercel-bundle/index/$INGEST_RUN_ID/"
# Optional: full vector search on Vercel (add Pinecone deps + secrets — see docs/VERCEL.md)
# cp "data/index/$INGEST_RUN_ID/index_manifest.json" "vercel-bundle/index/$INGEST_RUN_ID/"
```

If you omit this bundle, the site still loads but the chatbot will report that no index is available until you add files and redeploy.
