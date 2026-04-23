import mf_chat.service as svc


def test_hdfc_question_on_edelweiss_only_index_no_sources(monkeypatch, tmp_path) -> None:
    root = tmp_path
    (root / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")
    rid = "run-amc"
    idx = root / "data" / "index" / rid
    idx.mkdir(parents=True)
    line = (
        '{"chunk_id":"1","source_url":"https://www.indmoney.com/mutual-funds/edelweiss-flexi-cap-fund-direct-growth-3174",'
        '"scheme_name":"Edelweiss Flexi Cap Fund","kind":"snapshot",'
        '"text":"NAV as on 22 Apr 2026 Rs 44.95"}'
    )
    (idx / "chunks.jsonl").write_text(line + "\n", encoding="utf-8")

    monkeypatch.setattr(svc, "project_root", lambda: root)

    out = svc.chat("what is nav for HDFC", rid)
    assert out.ingest_run_id == rid
    assert not out.source_urls
    assert not out.sources
    assert "out of scope" in out.answer.lower() or "isn’t in the indexed" in out.answer.lower()


def test_edelweiss_question_still_works(monkeypatch, tmp_path) -> None:
    root = tmp_path
    (root / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")
    rid = "run-ok"
    idx = root / "data" / "index" / rid
    idx.mkdir(parents=True)
    line = (
        '{"chunk_id":"1","source_url":"https://www.indmoney.com/mutual-funds/edelweiss-flexi-cap-fund-direct-growth-3174",'
        '"scheme_name":"Edelweiss Flexi Cap Fund","kind":"snapshot",'
        '"text":"NAV as on 22 Apr 2026 Rs 44.95"}'
    )
    (idx / "chunks.jsonl").write_text(line + "\n", encoding="utf-8")

    monkeypatch.setattr(svc, "project_root", lambda: root)

    out = svc.chat("NAV for Edelweiss Flexi Cap", rid)
    assert out.source_urls
    assert "44.95" in out.answer or "nav" in out.answer.lower()


def test_mentioned_amc_tokens() -> None:
    from mf_chat.relevance import mentioned_amc_tokens

    assert "hdfc" in mentioned_amc_tokens("What is NAV for HDFC?")
    assert not mentioned_amc_tokens("What is NAV?")


def test_query_names_amc_outside_indexed_hits() -> None:
    from mf_chat.relevance import query_names_amc_outside_indexed_hits

    hits = [
        (
            {
                "scheme_name": "Edelweiss Flexi Cap Fund",
                "source_url": "https://www.indmoney.com/mutual-funds/edelweiss-flexi-cap-fund-direct-growth-3174",
                "text": "x",
            },
            1.0,
        )
    ]
    assert query_names_amc_outside_indexed_hits("nav for hdfc", hits)
    assert not query_names_amc_outside_indexed_hits("nav for edelweiss", hits)
