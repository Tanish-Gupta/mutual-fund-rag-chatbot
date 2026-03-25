from pathlib import Path

from mf_ingest.indmoney_parser import parse_indmoney_html

FIXTURE = Path(__file__).parent / "fixtures" / "indmoney_emerging_markets_fixture.html"
URL = "https://www.indmoney.com/mutual-funds/edelweiss-emerging-markets-opportunities-equity-offshore-direct-growth-5466"


def test_fixture_snapshot_and_sections() -> None:
    html = FIXTURE.read_text(encoding="utf-8")
    out = parse_indmoney_html(html, URL)

    assert out.scheme_name and "Emerging Markets" in out.scheme_name
    assert out.snapshot.get("nav_value") == "25.81"
    assert out.snapshot.get("nav_as_on") == "20 Mar 2026"
    assert out.snapshot.get("return_since_inception") == "8.43%"
    assert out.snapshot.get("expense_ratio") == "1.48%"
    assert out.snapshot.get("benchmark") == "MSCI EM NR INR"
    assert out.snapshot.get("min_lumpsum_sip") == "--/₹100"
    assert out.snapshot.get("turnover") == "13.11%"
    assert out.snapshot.get("aum_cr") == "203"
    assert out.snapshot.get("exit_load") == "1.0%"
    assert out.snapshot.get("lock_in") == "No Lock-in"
    assert "about" in out.sections
    assert "taxation" in out.sections
    assert "returns" in out.sections
    assert len(out.fund_managers) == 2
    names = {m["name"] for m in out.fund_managers}
    assert names == {"Bharat Lahoti", "Bhavesh Jain"}
