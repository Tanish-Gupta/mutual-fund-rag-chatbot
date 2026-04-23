# Daily scheduler (10:00 local for launchd/cron; 10:00 IST for GitHub Actions) — ingest + index

Phase 5 is automated by running `scripts/run_daily_pipeline.sh` once per day. It executes the same flow as `mf-pipeline`: fetch default seed URLs, parse, then `mf-index build` (Chroma by default). Logs append under `data/logs/`.

To print the documented schedule (GitHub cron + summary): `mf-pipeline --schedule-info` (or `python -m mf_pipeline --schedule-info` with `PYTHONPATH` set).

**Requirements on the host:** `python3` with project deps (`pip install -e ".[vector]"` and optional `pip install -e ".[browser]"` if you use `MF_PIPELINE_BROWSER=1`), and network access to allowlisted sites.

---

## GitHub Actions (cloud scheduler)

Workflow: [`.github/workflows/daily-pipeline.yml`](../.github/workflows/daily-pipeline.yml)

- **Triggers:** daily at **04:30 UTC** (= **10:00 India Standard Time**, IST has no DST) and **manual** (`workflow_dispatch`). Cron: `30 4 * * *` — must match `phase5/src/mf_pipeline/schedule.py` → `GITHUB_ACTIONS_CRON_UTC`.
- **Steps:** Python 3.12 → `pip install -e ".[vector]"` → `python -m mf_pipeline --index-backend chroma` (adds `--browser` when `MF_PIPELINE_BROWSER=1`).
- **Artifacts:** uploads `data/manifests/*.json`, `data/index/*/index_manifest.json`, and `data/index/*/chunks.jsonl` (retained 14 days). Vector DB dirs under `data/index/` stay on the runner only (large); download the artifact if you need manifests/chunks for debugging.

**Repo settings (optional):**

| Name | Type | Purpose |
|------|------|---------|
| `MF_PIPELINE_BROWSER` | Variable (`0` / `1`) | `1` installs Playwright + Chromium and passes `--browser` to ingest (use if IndMoney blocks plain HTTP from GitHub IPs). |
| `HF_TOKEN` | Secret | Optional Hugging Face token for faster / higher-rate embedding model downloads. |

**Git identity check (local machine):** ensure commits use the account you expect:

```bash
git config user.email          # should match your GitHub-verified email if you want clean attribution
git remote -v                  # origin should point at github.com/<org-or-user>/<repo>.git
gh auth status                 # optional: GitHub CLI login
gh api user -q .login          # GitHub username (public email may be empty if hidden in profile)
```

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

Add a line from `deploy/cron.mf-rag.example` (adjust the path). `0 10 * * *` means **10:00 every day** in the server’s local timezone.

---

## Environment

- **`.env`** in the repo root is picked up inside `mf_pipeline` (Groq / Pinecone not required for the scheduled job unless you change the pipeline).
- **`MF_PIPELINE_BROWSER=1`** — pass Playwright-based fetch (heavier; use if HTTP fetch fails under cron/launchd).
To add extra seed URLs for a scheduled run, either edit `DEFAULT_SEED_URLS` in `phase1/src/mf_ingest/config.py` or wrap this script in your own shell script that calls `python3 -m mf_pipeline` with `--url` flags.

---

## After a successful run

The chat API (`mf-chat`) uses **latest** index under `data/index/` by default. If the API is already running, it will pick up the new run on the next request (no restart required unless you cache manifests in memory elsewhere).
