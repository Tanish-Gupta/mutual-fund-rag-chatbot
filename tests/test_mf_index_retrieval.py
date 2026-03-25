from mf_index.retrieval import retrieve


def test_retrieve_returns_chunks_with_scores() -> None:
    chunks = [
        {
            "chunk_id": "1",
            "source_url": "https://www.indmoney.com/mutual-funds/foo-1",
            "scheme_name": "Foo Fund",
            "kind": "snapshot",
            "text": "Scheme: Foo Fund\nexpense_ratio: 1.2%\nbenchmark: NIFTY 50",
        },
        {
            "chunk_id": "2",
            "source_url": "https://www.indmoney.com/mutual-funds/bar-2",
            "scheme_name": "Bar Fund",
            "kind": "snapshot",
            "text": "Scheme: Bar Fund\nlock_in: 3 years",
        },
    ]
    hits = retrieve("What is the expense ratio?", chunks, top_k=3)
    assert len(hits) >= 1
    assert hits[0][0]["source_url"] == "https://www.indmoney.com/mutual-funds/foo-1"
