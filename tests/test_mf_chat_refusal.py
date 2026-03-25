import mf_chat.service as svc
from mf_chat.routing import Intent, classify_message


def test_refuse_advice_before_retrieval(monkeypatch, tmp_path) -> None:
    root = tmp_path
    (root / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")
    monkeypatch.setattr(svc, "project_root", lambda: root)

    out = svc.chat("Which fund should I buy?", None)
    assert "buy" in out.answer.lower() or "sell" in out.answer.lower() or "advice" in out.answer.lower()
    assert out.ingest_run_id == ""
    assert len(out.source_urls) >= 1
    assert any("amfiindia.com" in u for u in out.source_urls)
    assert any("sebi" in u for u in out.source_urls)


def test_refuse_sell_question(monkeypatch, tmp_path) -> None:
    assert classify_message("Should I sell my mutual fund now?") == Intent.REFUSE_ADVICE
    root = tmp_path
    (root / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")
    monkeypatch.setattr(svc, "project_root", lambda: root)
    out = svc.chat("Should I sell my mutual fund now?", None)
    assert out.ingest_run_id == ""
    assert "sell" in out.answer.lower() or "buy" in out.answer.lower()
