# Daily scheduler (12:00 local) — ingest + index

Phase 5 is automated by running `scripts/run_daily_pipeline.sh` once per day. It executes the same flow as `mf-pipeline`: fetch default seed URLs, parse, then `mf-index build` (Chroma by default). Logs append under `data/logs/`.

**Requirements on the host:** `python3` with project deps (`pip install -e ".[vector]"` and optional `pip install -e ".[browser]"` if you use `MF_PIPELINE_BROWSER=1`), and network access to allowlisted sites.

---

## macOS — `launchd` (recommended)

1. Install the LaunchAgent (replace the path with your clone; works with spaces in the path):

   ```bash
   cd "/path/to/Mutual Fund RAG chat Bot"
   sed "s|PROJECT_ROOT|$(pwd)|g" deploy/launchd/com.mf-rag.daily-pipeline.plist > ~/Library/LaunchAgents/com.mf-rag.daily-pipeline.plist
   ```

2. Make the script executable:

   ```bash
   chmod +x scripts/run_daily_pipeline.sh
   ```

3. Load the agent:

   ```bash
   launchctl load ~/Library/LaunchAgents/com.mf-rag.daily-pipeline.plist
   ```

4. Verify it’s loaded:

   ```bash
   launchctl list | grep mf-rag
   ```

**Unload / disable:** `launchctl unload ~/Library/LaunchAgents/com.mf-rag.daily-pipeline.plist`

**Run once now (test):**  
`launchctl start com.mf-rag.daily-pipeline`

---

## cron (Linux or macOS)

```bash
chmod +x scripts/run_daily_pipeline.sh
crontab -e
```

Add a line from `deploy/cron.mf-rag.example` (adjust the path). `0 12 * * *` means **12:00 every day** in the server’s local timezone.

---

## Environment

- **`.env`** in the repo root is picked up inside `mf_pipeline` (Groq / Pinecone not required for the scheduled job unless you change the pipeline).
- **`MF_PIPELINE_BROWSER=1`** — pass Playwright-based fetch (heavier; use if HTTP fetch fails under cron/launchd).
To add extra seed URLs for a scheduled run, either edit `DEFAULT_SEED_URLS` in `phase1/src/mf_ingest/config.py` or wrap this script in your own shell script that calls `python3 -m mf_pipeline` with `--url` flags.

---

## After a successful run

The chat API (`mf-chat`) uses **latest** index under `data/index/` by default. If the API is already running, it will pick up the new run on the next request (no restart required unless you cache manifests in memory elsewhere).
