import json

from mf_index.retrieval import retrieve_from_manifest


def test_retrieve_from_manifest_uses_vector_then_jsonl(monkeypatch, tmp_path) -> None:
    root = tmp_path
    rid = "run-a"
    idx = root / "data" / "index" / rid
    idx.mkdir(parents=True)
    chunk = {
        "chunk_id": "c1",
        "text": "expense ratio 1.2% benchmark nifty",
        "source_url": "https://www.indmoney.com/mutual-funds/foo",
        "scheme_name": "Foo Fund",
        "kind": "snapshot",
    }
    (idx / "chunks.jsonl").write_text(json.dumps(chunk) + "\n")
    manifest = {
        "ingest_run_id": rid,
        "backend": "chroma",
        "chroma_path": f"data/index/{rid}/chroma_db",
        "chroma_collection": f"mf_rag_{rid.replace('-', '_')}",
        "embedding_model": "stub-model",
    }

    monkeypatch.setattr(
        "mf_index.retrieval.embed_query",
        lambda q, model_name="stub-model": [0.01] * 384,
    )

    def fake_chroma(
        persist_dir,
        collection_name,
        query_embedding,
        top_k,
    ):
        assert len(query_embedding) == 384
        return [("c1", 0.9)]

    monkeypatch.setattr("mf_index.vector_store.chroma_query", fake_chroma)

    hits = retrieve_from_manifest("expense ratio", root, manifest, top_k=3)
    assert len(hits) == 1
    assert hits[0][0]["chunk_id"] == "c1"
    assert hits[0][0]["source_url"].endswith("/foo")
