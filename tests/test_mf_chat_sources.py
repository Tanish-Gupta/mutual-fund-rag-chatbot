from mf_chat.service import chat


def test_chat_returns_source_urls_for_hits(monkeypatch, tmp_path) -> None:
    import mf_chat.service as svc

    root = tmp_path
    (root / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")
    rid = "test-run"
    idx = root / "data" / "index" / rid
    idx.mkdir(parents=True)
    line = (
        '{"chunk_id":"a","source_url":"https://www.indmoney.com/mutual-funds/x",'
        '"scheme_name":"X Fund","kind":"snapshot",'
        '"text":"Scheme: X Fund\\nexpense_ratio: 0.5%"}'
    )
    (idx / "chunks.jsonl").write_text(line + "\n", encoding="utf-8")

    monkeypatch.setattr(svc, "project_root", lambda: root)

    out = chat("expense ratio", rid)
    assert out.ingest_run_id == rid
    assert "https://www.indmoney.com/mutual-funds/x" in out.source_urls
    assert out.sources and out.sources[0].url.endswith("/x")
