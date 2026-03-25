from pathlib import Path

from fastapi.testclient import TestClient


def test_index_meta_no_index(monkeypatch, tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")

    import mf_chat.paths as p

    monkeypatch.setattr(p, "project_root", lambda: tmp_path)

    from mf_chat.app import app

    c = TestClient(app)
    r = c.get("/api/index-meta")
    assert r.status_code == 200
    data = r.json()
    assert data["ingest_run_id"] is None
    assert data["last_updated_iso"] is None


def test_index_meta_with_manifest(monkeypatch, tmp_path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname='t'\nversion='0'\n", encoding="utf-8")
    rid = "run-xyz"
    idx = tmp_path / "data" / "index" / rid
    idx.mkdir(parents=True)
    (idx / "index_manifest.json").write_text('{"ingest_run_id":"run-xyz"}', encoding="utf-8")

    import mf_chat.paths as p

    monkeypatch.setattr(p, "project_root", lambda: tmp_path)

    from mf_chat.app import app

    c = TestClient(app)
    r = c.get("/api/index-meta")
    assert r.status_code == 200
    data = r.json()
    assert data["ingest_run_id"] == rid
    assert data["last_updated_iso"] is not None
    assert data["last_updated_iso"].endswith("Z")
