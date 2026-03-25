from __future__ import annotations

import json
import re
from typing import Any

from bs4 import BeautifulSoup

from mf_ingest.models import SchemePageStructured


def _get_mf_detail_data(next_data: dict[str, Any]) -> dict[str, Any] | None:
    """Navigate to IndMoney mutual fund detail payload inside __NEXT_DATA__."""
    props = next_data.get("props")
    if not isinstance(props, dict):
        return None
    pp = props.get("pageProps")
    if not isinstance(pp, dict):
        return None
    mfd = pp.get("mutualFundsDetailData")
    if not isinstance(mfd, dict):
        return None
    inner = mfd.get("data")
    if isinstance(inner, dict):
        return inner
    return None


def _parse_nav_numeric(nav: str | None) -> str | None:
    if not nav:
        return None
    m = re.search(r"([\d,.]+)", nav.replace(",", ""))
    return m.group(1) if m else None


def _parse_aum_cr(value: str | None) -> str | None:
    if not value:
        return None
    m = re.search(r"([\d,.]+)\s*Cr", value, re.IGNORECASE)
    return m.group(1).replace(",", "") if m else None


def _fund_overview_map(data: dict[str, Any]) -> dict[str, str | None]:
    """Map fund_overview.info name/value pairs to snapshot keys."""
    out: dict[str, str | None] = {}
    fo = data.get("fund_overview")
    if not isinstance(fo, dict):
        return out
    info = fo.get("info")
    if not isinstance(info, list):
        return out

    for item in info:
        if not isinstance(item, dict):
            continue
        raw_name = (item.get("name") or "").strip().lower()
        val = item.get("value")
        desc = item.get("description")
        if val is not None and not isinstance(val, str):
            val = str(val)
        if desc is not None and not isinstance(desc, str):
            desc = str(desc)

        if raw_name == "expense ratio":
            out["expense_ratio"] = val
        elif raw_name == "benchmark":
            out["benchmark"] = val
        elif raw_name == "aum":
            out["aum_cr"] = _parse_aum_cr(val) or val
        elif raw_name == "inception date":
            out["inception_date"] = val
        elif raw_name == "min lumpsum/sip":
            out["min_lumpsum_sip"] = val
        elif raw_name == "exit load":
            out["exit_load"] = val
            if desc:
                out["exit_load_detail"] = desc
        elif raw_name == "lock in":
            out["lock_in"] = val
        elif raw_name == "turnover":
            out["turnover"] = val

    return out


def _risk_from_api(data: dict[str, Any]) -> str | None:
    rm = data.get("risk_meter")
    if not isinstance(rm, dict):
        return None
    wp = rm.get("widget_properties")
    if not isinstance(wp, dict):
        return None
    zt = wp.get("zone_title")
    if isinstance(zt, str) and zt.strip():
        return zt.strip()
    body = wp.get("body")
    if isinstance(body, str) and "Very High Risk" in body:
        return "Very High Risk"
    if isinstance(body, str) and "at " in body:
        m = re.search(r"at\s+(.+)$", body.strip())
        if m:
            return m.group(1).strip().rstrip(".")
    return None


def _fund_managers_from_api(data: dict[str, Any]) -> list[dict[str, str | None]]:
    about = data.get("about")
    if not isinstance(about, dict):
        return []
    mgr = about.get("managers")
    if not isinstance(mgr, dict):
        return []
    wp = mgr.get("widget_properties")
    if not isinstance(wp, dict):
        return []
    cd = wp.get("card_data")
    if not isinstance(cd, dict):
        return []
    infos = cd.get("managers_info")
    if not isinstance(infos, list):
        return []

    result: list[dict[str, str | None]] = []
    for row in infos:
        if not isinstance(row, dict):
            continue
        title = row.get("title")
        subtitle = row.get("subtitle")
        if not isinstance(title, str):
            continue
        since = None
        if isinstance(subtitle, str):
            sm = re.search(r"since\s+(.+)$", subtitle, re.IGNORECASE)
            if sm:
                since = sm.group(1).strip()
        result.append({"name": title.strip(), "since": since})
    return result


def _header_id_int(raw: Any) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _extract_performance_table(data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Parse fund_performance.widget_properties.card_data.table into headers + row dicts.
    Each row maps column title (e.g. 'This Fund', 'Nifty 50 TRI') -> cell value.
    """
    fp = data.get("fund_performance")
    if not isinstance(fp, dict):
        return None
    wp = fp.get("widget_properties")
    if not isinstance(wp, dict):
        return None
    cd = wp.get("card_data")
    if not isinstance(cd, dict):
        return None
    table = cd.get("table")
    if not isinstance(table, dict):
        return None

    raw_headers = table.get("columnHeader")
    raw_rows = table.get("rows")
    if not isinstance(raw_headers, list) or not isinstance(raw_rows, list):
        return None

    id_to_title: dict[int, str] = {}
    for h in raw_headers:
        if not isinstance(h, dict):
            continue
        hid = _header_id_int(h.get("id"))
        title = h.get("title")
        if hid and isinstance(title, str) and title.strip():
            id_to_title[hid] = title.strip()

    if not id_to_title:
        return None

    out_rows: list[dict[str, str]] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        cols = row.get("columns")
        if not isinstance(cols, list):
            continue
        row_map: dict[str, str] = {}
        for cell in cols:
            if not isinstance(cell, dict):
                continue
            hid = _header_id_int(cell.get("headerId"))
            title = cell.get("title")
            if hid not in id_to_title or title is None:
                continue
            row_map[id_to_title[hid]] = str(title)
        if row_map:
            out_rows.append(row_map)

    if not out_rows:
        return None

    column_headers_ordered = [id_to_title[k] for k in sorted(id_to_title.keys())]

    return {
        "display_name": cd.get("display_name") if isinstance(cd.get("display_name"), str) else None,
        "display_subtitle": cd.get("display_subtitle") if isinstance(cd.get("display_subtitle"), str) else None,
        "as_on": cd.get("as_on") if isinstance(cd.get("as_on"), str) else None,
        "highlight_text": cd.get("highlight_text") if isinstance(cd.get("highlight_text"), str) else None,
        "column_headers": column_headers_ordered,
        "rows": out_rows,
    }


def _snapshot_from_api_data(data: dict[str, Any]) -> dict[str, str | None]:
    snap: dict[str, str | None] = {}

    nav = data.get("nav")
    if isinstance(nav, str):
        snap["nav_value"] = _parse_nav_numeric(nav)
    snap["nav_as_on"] = data.get("nav_date") if isinstance(data.get("nav_date"), str) else None

    odc = data.get("one_day_change")
    if isinstance(odc, (int, float)):
        snap["one_day_change_percent"] = str(odc)

    ir = data.get("inception_return")
    if isinstance(ir, (int, float)):
        snap["return_since_inception"] = f"{ir}%"
    elif isinstance(ir, str) and ir.strip():
        snap["return_since_inception"] = ir.strip() if "%" in ir else f"{ir.strip()}%"

    meta = data.get("meta_info")
    if isinstance(meta, dict) and not snap.get("return_since_inception"):
        ir2 = meta.get("interest_rate")
        if isinstance(ir2, str) and ir2.strip():
            snap["return_since_inception"] = ir2.strip()

    snap.update(_fund_overview_map(data))

    risk = _risk_from_api(data)
    if risk:
        snap["risk"] = risk

    return snap


def _merge_snapshots(
    api_snap: dict[str, str | None],
    regex_snap: dict[str, str | None],
) -> dict[str, str | None]:
    """Prefer API (__NEXT_DATA__) values; fill gaps from regex/HTML heuristics."""
    out = {**regex_snap}
    for k, v in api_snap.items():
        if v is not None and str(v).strip() != "":
            out[k] = v
    return out


def _extract_next_data_json(html: str) -> dict[str, Any] | None:
    m = re.search(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>([^<]+)</script>',
        html,
        re.IGNORECASE,
    )
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


def _visible_text_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    return [ln for ln in lines if ln]


def _first_h1(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    h1 = soup.find("h1")
    if h1 and h1.get_text(strip=True):
        return h1.get_text(strip=True)
    return None


def _extract_snapshot(lines: list[str], blob: str) -> dict[str, str | None]:
    snap: dict[str, str | None] = {}

    # NAV line often: "₹25.81 ▼-0.2 1D NAV as on 20 Mar 2026"
    nav_m = re.search(
        r"₹?\s*([\d,.]+)\s*.*?NAV\s+as\s+on\s+(.+?)(?:\n|$)",
        blob,
        re.IGNORECASE | re.DOTALL,
    )
    if nav_m:
        snap["nav_value"] = nav_m.group(1).replace(",", "")
        snap["nav_as_on"] = nav_m.group(2).strip()

    si = re.search(
        r"([\d.]+%)\s*/?\s*per\s+year\s+Since\s+Inception",
        blob,
        re.IGNORECASE,
    )
    if si:
        snap["return_since_inception"] = si.group(1)

    er = re.search(r"Expense\s+ratio\s*([\d.]+%)", blob, re.IGNORECASE)
    if er:
        snap["expense_ratio"] = er.group(1)

    bm = re.search(r"Benchmark\s+([^\n]+)", blob, re.IGNORECASE)
    if bm:
        snap["benchmark"] = bm.group(1).strip()

    aum = re.search(r"AUM\s*₹?\s*([\d,.]+)\s*Cr", blob, re.IGNORECASE)
    if aum:
        snap["aum_cr"] = aum.group(1).replace(",", "")

    inc = re.search(r"Inception\s+Date\s+([^\n]+)", blob, re.IGNORECASE)
    if inc:
        snap["inception_date"] = inc.group(1).strip()

    minls = re.search(
        r"Min\s+Lumpsum/SIP\s+(.+?)(?:\n|Exit\s+Load)",
        blob,
        re.IGNORECASE | re.DOTALL,
    )
    if minls:
        snap["min_lumpsum_sip"] = re.sub(r"\s+", " ", minls.group(1)).strip()

    el = re.search(r"Exit\s+Load\s+(.+?)(?:\n|Lock)", blob, re.IGNORECASE | re.DOTALL)
    if el:
        snap["exit_load"] = re.sub(r"\s+", " ", el.group(1)).strip()

    lk = re.search(r"Lock\s*In\s+(.+?)(?:\n|Turn)", blob, re.IGNORECASE | re.DOTALL)
    if lk:
        snap["lock_in"] = re.sub(r"\s+", " ", lk.group(1)).strip()

    to = re.search(r"Turn\s*Over\s+([\d.]+%)", blob, re.IGNORECASE)
    if to:
        snap["turnover"] = to.group(1)

    risk = re.search(
        r"Risk\s*\n?\s*(Very High Risk|Very Low Risk|Low Risk|Moderate Risk|High Risk|Moderately High Risk|Moderately Low Risk)",
        blob,
        re.IGNORECASE,
    )
    if risk:
        snap["risk"] = risk.group(1).strip()
    else:
        risk_loose = re.search(r"Risk\s+(.+?)(?:\nAbout|\nKey Parameters|\nReturns|\Z)", blob, re.IGNORECASE | re.DOTALL)
        if risk_loose:
            candidate = re.sub(r"\s+", " ", risk_loose.group(1)).strip()
            if len(candidate) < 80 and "INDmoney" not in candidate:
                snap["risk"] = candidate

    return snap


def _split_sections(blob: str) -> dict[str, str]:
    markers: list[tuple[str, str]] = [
        ("about", r"(About\s+.+\s+Fund)"),
        ("key_parameters", r"(Key\s+Parameters)"),
        ("returns", r"(Returns)"),
        ("holdings", r"(Holdings)"),
        ("taxation", r"(Taxation)"),
        ("investment_objective", r"(Investment\s+objective\s+of\s+.+\s+Fund)"),
        ("minimum_investment", r"(Minimum\s+Investment\s+and\s+lockin\s+period)"),
        ("know_more", r"(Know\s+more\s+about\s+.+\s+Fund)"),
    ]
    found: list[tuple[int, str, str]] = []
    for key, pat in markers:
        m = re.search(pat, blob, re.IGNORECASE)
        if m:
            found.append((m.start(), key, m.group(1)))
    found.sort(key=lambda x: x[0])

    sections: dict[str, str] = {}
    for i, (_pos, key, _title) in enumerate(found):
        start = found[i][0]
        end = found[i + 1][0] if i + 1 < len(found) else len(blob)
        block = blob[start:end].strip()
        if block:
            sections[key] = block
    return sections


def _extract_fund_managers(blob: str) -> list[dict[str, str | None]]:
    """IndMoney pattern: name line, then 'Fund Manager of <scheme>, since <date>'."""
    managers: list[dict[str, str | None]] = []
    pat = re.compile(
        r"(?m)^(?P<name>[^\n]+)\nFund Manager of .+?, since (?P<since>.+)$",
        re.IGNORECASE,
    )
    for m in pat.finditer(blob):
        name = m.group("name").strip()
        since = m.group("since").strip()
        if name.lower() == "fund manager":
            continue
        managers.append({"name": name, "since": since})
    return managers


def _next_data_debug_subset(data: dict[str, Any]) -> dict[str, Any] | None:
    """Keep a small JSON-safe slice for manifests (avoid huge blobs)."""
    props = data.get("props", {})
    pp = props.get("pageProps")
    if isinstance(pp, dict):
        keys = [k for k in pp.keys() if not k.startswith("_")][:40]
        return {k: _truncate_json(pp[k]) for k in keys}
    return None


def _truncate_json(val: Any, max_len: int = 2000) -> Any:
    if isinstance(val, dict):
        return {str(k): _truncate_json(v, max_len) for k, v in list(val.items())[:30]}
    if isinstance(val, list):
        return [_truncate_json(x, max_len) for x in val[:20]]
    if isinstance(val, str) and len(val) > max_len:
        return val[:max_len] + "…"
    return val


def parse_indmoney_html(html: str, source_url: str) -> SchemePageStructured:
    lines = _visible_text_lines(html)
    blob = "\n".join(lines)

    nd = _extract_next_data_json(html)
    detail = _get_mf_detail_data(nd) if nd else None

    scheme_name = _first_h1(html)
    if isinstance(detail, dict):
        n = detail.get("name") or detail.get("short_name")
        if isinstance(n, str) and n.strip():
            scheme_name = n.strip()
    if not scheme_name:
        for ln in lines[:15]:
            if "fund" in ln.lower() and len(ln) > 10 and "₹" not in ln[:3]:
                scheme_name = ln
                break

    regex_snap = _extract_snapshot(lines, blob)
    api_snap = _snapshot_from_api_data(detail) if detail else {}
    snap = _merge_snapshots(api_snap, regex_snap)

    sections = _split_sections(blob)
    managers = _extract_fund_managers(blob)
    api_managers = _fund_managers_from_api(detail) if detail else []
    if api_managers:
        managers = api_managers

    nd_sub = _next_data_debug_subset(nd) if nd else None
    perf_table = _extract_performance_table(detail) if detail else None

    return SchemePageStructured(
        source_url=source_url,
        scheme_name=scheme_name,
        snapshot=snap,
        sections=sections,
        fund_managers=managers,
        performance_table=perf_table,
        next_data_snippet=nd_sub,
    )
