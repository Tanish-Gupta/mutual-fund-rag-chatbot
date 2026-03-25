import json

from mf_ingest.indmoney_parser import parse_indmoney_html

URL = "https://www.indmoney.com/mutual-funds/example-direct-growth-9999"


def test_snapshot_prefers_mutual_funds_detail_api() -> None:
    payload = {
        "props": {
            "pageProps": {
                "mutualFundsDetailData": {
                    "success": True,
                    "data": {
                        "name": "API Scheme Name",
                        "nav": "₹10.55",
                        "nav_date": "15 Mar 2026",
                        "one_day_change": -0.3,
                        "inception_return": 7.25,
                        "fund_overview": {
                            "info": [
                                {"name": "Expense ratio", "value": "0.88%"},
                                {"name": "Benchmark", "value": "NIFTY 500 TRI"},
                                {"name": "AUM", "value": "₹1,234 Cr"},
                                {"name": "Inception Date", "value": "1 Jan 2010"},
                                {"name": "Min Lumpsum/SIP", "value": "₹500/₹100"},
                                {
                                    "name": "Exit Load",
                                    "value": "1.0%",
                                    "description": "Exit load details here",
                                },
                                {"name": "Lock In", "value": "3 years"},
                                {"name": "TurnOver", "value": "20%"},
                            ]
                        },
                        "risk_meter": {
                            "widget_properties": {
                                "zone_title": "Very High Risk",
                                "body": "Investors understand…",
                            }
                        },
                        "about": {
                            "managers": {
                                "widget_properties": {
                                    "card_data": {
                                        "managers_info": [
                                            {
                                                "title": "Jane Doe",
                                                "subtitle": "Fund Manager of API Scheme, since 1 June 2020",
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        "fund_performance": {
                            "widget_properties": {
                                "card_data": {
                                    "display_name": "API Scheme vs Benchmark",
                                    "display_subtitle": "Fund returns vs Benchmark",
                                    "as_on": "as on (01-Jan-26)",
                                    "highlight_text": "Sample highlight.",
                                    "table": {
                                        "columnHeader": [
                                            {"id": 1, "title": "Metric"},
                                            {"id": 2, "title": "This Fund"},
                                            {"id": 3, "title": "Benchmark X"},
                                            {"id": 4, "title": "Category Avg"},
                                        ],
                                        "rows": [
                                            {
                                                "columns": [
                                                    {"title": "1M", "headerId": 1},
                                                    {"title": "-1.0%", "headerId": 2},
                                                    {"title": "-2.0%", "headerId": 3},
                                                    {"title": "--", "headerId": 4},
                                                ]
                                            },
                                            {
                                                "columns": [
                                                    {"title": "1Y", "headerId": 1},
                                                    {"title": "12.5%", "headerId": 2},
                                                    {"title": "10.0%", "headerId": 3},
                                                    {"title": "9.0%", "headerId": 4},
                                                ]
                                            },
                                        ],
                                    },
                                }
                            }
                        },
                    },
                }
            }
        }
    }
    script = json.dumps(payload, separators=(",", ":"))
    html = f"""<!DOCTYPE html><html><head><title>x</title></head><body>
<h1>Wrong Title From HTML</h1>
<p>Risk management and cost efficiency noise</p>
<script id="__NEXT_DATA__" type="application/json">{script}</script>
</body></html>"""

    out = parse_indmoney_html(html, URL)

    assert out.scheme_name == "API Scheme Name"
    assert out.snapshot["nav_value"] == "10.55"
    assert out.snapshot["nav_as_on"] == "15 Mar 2026"
    assert out.snapshot["one_day_change_percent"] == "-0.3"
    assert out.snapshot["return_since_inception"] == "7.25%"
    assert out.snapshot["expense_ratio"] == "0.88%"
    assert out.snapshot["benchmark"] == "NIFTY 500 TRI"
    assert out.snapshot["aum_cr"] == "1234"
    assert out.snapshot["inception_date"] == "1 Jan 2010"
    assert out.snapshot["min_lumpsum_sip"] == "₹500/₹100"
    assert out.snapshot["exit_load"] == "1.0%"
    assert out.snapshot["exit_load_detail"] == "Exit load details here"
    assert out.snapshot["lock_in"] == "3 years"
    assert out.snapshot["turnover"] == "20%"
    assert out.snapshot["risk"] == "Very High Risk"
    assert len(out.fund_managers) == 1
    assert out.fund_managers[0]["name"] == "Jane Doe"
    assert out.fund_managers[0]["since"] == "1 June 2020"

    assert out.performance_table is not None
    assert out.performance_table["as_on"] == "as on (01-Jan-26)"
    assert out.performance_table["highlight_text"] == "Sample highlight."
    assert out.performance_table["column_headers"] == [
        "Metric",
        "This Fund",
        "Benchmark X",
        "Category Avg",
    ]
    assert out.performance_table["rows"] == [
        {
            "Metric": "1M",
            "This Fund": "-1.0%",
            "Benchmark X": "-2.0%",
            "Category Avg": "--",
        },
        {
            "Metric": "1Y",
            "This Fund": "12.5%",
            "Benchmark X": "10.0%",
            "Category Avg": "9.0%",
        },
    ]
