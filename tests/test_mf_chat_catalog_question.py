import mf_chat.service as svc


def test_catalog_style_question_returns_all_sources(monkeypatch, tmp_path) -> None:
    """Questions like 'what funds can you answer about' must not use Groq+top-1 source."""
    root = tmp_path
    (root / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")
    rid = "run-cat"
    idx = root / "data" / "index" / rid
    idx.mkdir(parents=True)
    lines = [
        '{"chunk_id":"0","source_url":"https://ex.com/a","scheme_name":"Fund A","text":"x"}',
        '{"chunk_id":"1","source_url":"https://ex.com/b","scheme_name":"Fund B","text":"y"}',
        '{"chunk_id":"2","source_url":"https://ex.com/c","scheme_name":"Fund C","text":"z"}',
    ]
    (idx / "chunks.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")

    monkeypatch.setattr(svc, "project_root", lambda: root)

    out = svc.chat("what all mutual funds can you answer about", rid)
    assert len(out.source_urls) == 3
    assert len(out.sources) == 3
