import mf_chat.service as svc


def test_groq_path_when_key_and_mocked_http(monkeypatch, tmp_path) -> None:
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
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    class FakeResp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"choices": [{"message": {"content": "The expense ratio is 0.5% per the index."}}]}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def post(self, url, **kwargs):  # noqa: ANN001
            return FakeResp()

    monkeypatch.setattr("mf_chat.groq_client.httpx.Client", FakeClient)

    out = svc.chat("expense ratio", rid)
    assert out.ingest_run_id == rid
    assert "0.5%" in out.answer or "expense" in out.answer.lower()
    assert out.source_urls == ["https://www.indmoney.com/mutual-funds/x"]
