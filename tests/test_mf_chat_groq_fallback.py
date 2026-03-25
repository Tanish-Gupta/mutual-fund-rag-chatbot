import mf_chat.service as svc


def test_groq_cannot_find_falls_back_to_chunk_excerpts(monkeypatch, tmp_path) -> None:
    root = tmp_path
    (root / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")
    rid = "test-run"
    idx = root / "data" / "index" / rid
    idx.mkdir(parents=True)
    line = (
        '{"chunk_id":"a","source_url":"https://www.indmoney.com/mutual-funds/x",'
        '"scheme_name":"X Fund","kind":"snapshot",'
        '"text":"Scheme: X Fund\\nexit_load: 1.0% for redemptions within 1 year"}'
    )
    (idx / "chunks.jsonl").write_text(line + "\n", encoding="utf-8")

    monkeypatch.setattr(svc, "project_root", lambda: root)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    class FakeResp:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "choices": [
                    {"message": {"content": "I cannot find the exit load in the provided indexed excerpts."}}
                ]
            }

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

    out = svc.chat("exit load", rid)
    assert "exit" in out.answer.lower() or "1.0%" in out.answer
    assert "turned up" in out.answer.lower() or "exit_load" in out.answer.lower()
