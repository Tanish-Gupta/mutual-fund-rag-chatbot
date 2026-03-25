import mf_chat.service as svc


def test_directory_returns_all_unique_scheme_urls(monkeypatch, tmp_path) -> None:
    root = tmp_path
    (root / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")
    rid = "run-dir"
    idx = root / "data" / "index" / rid
    idx.mkdir(parents=True)
    lines = [
        '{"chunk_id":"a","source_url":"https://example.com/a","scheme_name":"A Fund","text":"x"}',
        '{"chunk_id":"b","source_url":"https://example.com/b","scheme_name":"B Fund","text":"y"}',
        '{"chunk_id":"c","source_url":"https://example.com/a","scheme_name":"A Fund","text":"z"}',
    ]
    (idx / "chunks.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    monkeypatch.setattr(svc, "project_root", lambda: root)

    out = svc.chat("List all indexed fund links please", rid)
    assert out.ingest_run_id == rid
    assert len(out.source_urls) == 2
    assert "https://example.com/a" in out.source_urls
    assert "https://example.com/b" in out.source_urls
    assert "2" in out.answer and "scheme" in out.answer.lower()


def test_broad_question_returns_all_hit_sources(monkeypatch, tmp_path) -> None:
    """Generic questions cite every distinct scheme URL in the retrieval shortlist."""
    root = tmp_path
    (root / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")
    rid = "run-multi"
    idx = root / "data" / "index" / rid
    idx.mkdir(parents=True)
    lines = [
        '{"chunk_id":"1","source_url":"https://www.indmoney.com/mutual-funds/foo",'
        '"scheme_name":"Foo","kind":"snapshot","text":"expense_ratio: 1% benchmark nifty"}',
        '{"chunk_id":"2","source_url":"https://www.indmoney.com/mutual-funds/bar",'
        '"scheme_name":"Bar","kind":"snapshot","text":"expense_ratio: 2% benchmark sensex"}',
    ]
    (idx / "chunks.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    monkeypatch.setattr(svc, "project_root", lambda: root)

    out = svc.chat("expense ratio and benchmark", rid)
    assert len(out.source_urls) == 2


def test_named_scheme_returns_single_source(monkeypatch, tmp_path) -> None:
    """When the user names one scheme, only that page is cited."""
    root = tmp_path
    (root / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")
    rid = "run-focus"
    idx = root / "data" / "index" / rid
    idx.mkdir(parents=True)
    lines = [
        '{"chunk_id":"1","source_url":"https://ex.com/emerging",'
        '"scheme_name":"Edelweiss Emerging Markets Opportunities Fund","text":"risk very high"}',
        '{"chunk_id":"2","source_url":"https://ex.com/europe",'
        '"scheme_name":"Edelweiss Europe Dynamic Fund","text":"risk high"}',
    ]
    (idx / "chunks.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    monkeypatch.setattr(svc, "project_root", lambda: root)

    out = svc.chat("What is the risk for Edelweiss Emerging Markets Opportunities?", rid)
    assert len(out.source_urls) == 1
    assert out.source_urls[0] == "https://ex.com/emerging"
