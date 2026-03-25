#!/usr/bin/env python3
"""Print equity allocation and equity-sector breakdown from processed ingest JSON (next_data_snippet API shape)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def project_root() -> Path:
    here = Path(__file__).resolve()
    for d in [here, *here.parents]:
        if (d / "pyproject.toml").is_file():
            return d
    raise SystemExit("Run from repo root (pyproject.toml not found)")


def extract_equity_sectors(doc: dict) -> tuple[str | None, list[tuple[str, str]], str | None]:
    """
    Returns (equity_allocation_str, [(sector_name, sector_perc), ...] for equity sleeve only, as_on_note).
    """
    nd = doc.get("next_data_snippet")
    if not isinstance(nd, dict):
        return None, [], None
    mfd = nd.get("mutualFundsDetailData")
    if not isinstance(mfd, dict):
        return None, [], None
    data = mfd.get("data")
    if not isinstance(data, dict):
        return None, [], None

    as_on_parts: list[str] = []

    equity_pct: str | None = None
    aa = data.get("asset_allocation")
    if isinstance(aa, dict):
        if isinstance(aa.get("as_on"), str):
            as_on_parts.append(aa["as_on"])
        dist = aa.get("distribution")
        if isinstance(dist, list):
            for block in dist:
                if not isinstance(block, dict):
                    continue
                if str(block.get("name", "")).strip().lower() == "equity":
                    p = block.get("perc")
                    equity_pct = str(p).strip() if p is not None else None
                    break

    sectors: list[tuple[str, str]] = []
    sa = data.get("sector_allocation")
    if isinstance(sa, dict):
        if isinstance(sa.get("as_on"), str) and sa["as_on"] not in as_on_parts:
            as_on_parts.append(sa["as_on"])
        dist = sa.get("distribution")
        if isinstance(dist, list):
            for block in dist:
                if not isinstance(block, dict):
                    continue
                if str(block.get("name", "")).strip().lower() != "equity":
                    continue
                raw = block.get("sectors")
                if not isinstance(raw, list):
                    continue
                for s in raw:
                    if not isinstance(s, dict):
                        continue
                    nm = s.get("name")
                    pc = s.get("perc")
                    if isinstance(nm, str) and nm.strip():
                        sectors.append((nm.strip(), str(pc).strip() if pc is not None else ""))

    note = " / ".join(as_on_parts) if as_on_parts else None
    return equity_pct, sectors, note


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--run-id",
        required=True,
        help="ingest_run_id under data/processed/<id>/",
    )
    args = ap.parse_args()
    proc = project_root() / "data" / "processed" / args.run_id
    if not proc.is_dir():
        print(f"No such directory: {proc}", file=sys.stderr)
        sys.exit(1)

    files = sorted(proc.glob("*.json"))
    if not files:
        print(f"No JSON files in {proc}", file=sys.stderr)
        sys.exit(1)

    for path in files:
        doc = json.loads(path.read_text(encoding="utf-8"))
        url = doc.get("source_url") or ""
        name = doc.get("scheme_name") or path.stem
        eq, sectors, as_on = extract_equity_sectors(doc)
        print("=" * 72)
        print(f"Fund: {name}")
        print(f"URL:  {url}")
        if as_on:
            print(f"As on (from JSON): {as_on}")
        if eq is None and not sectors:
            print("Equity allocation: (not found in next_data_snippet — page may differ or API block missing)")
            print("Sector breakdown:  (not found)")
            continue
        print(f"Equity allocation (of portfolio): {eq or '—'}")
        if sectors:
            print("Equity sleeve — sectors:")
            for sn, sp in sectors:
                print(f"  • {sn}: {sp}")
        else:
            print("Equity sleeve — sectors: (none listed in JSON)")


if __name__ == "__main__":
    main()
