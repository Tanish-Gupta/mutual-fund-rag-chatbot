"""
Vercel ASGI entry (must live under api/). Exposes the FundFacts FastAPI app.

Local dev: uvicorn mf_chat.app:app --reload
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _rel in ("phase1/src", "phase2/src", "phase3/src", "phase5/src"):
    _p = str(_ROOT / _rel)
    if _p not in sys.path:
        sys.path.insert(0, _p)

from mf_chat.app import app  # noqa: E402
