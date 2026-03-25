from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=2)
def _model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        raise ImportError(
            "sentence-transformers is required for Phase 2 embeddings. "
            "Install with: pip install -e '.[vector]'"
        ) from e
    return SentenceTransformer(model_name)


def embed_texts(
    texts: list[str],
    *,
    model_name: str = DEFAULT_EMBEDDING_MODEL,
    batch_size: int = 32,
    normalize: bool = True,
) -> list[list[float]]:
    """Batch-encode texts to dense vectors (cosine-friendly if normalize=True)."""
    if not texts:
        return []
    model = _model(model_name)
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        emb = model.encode(
            batch,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
            show_progress_bar=False,
        )
        out.extend(emb.tolist())
    return out


def embed_query(text: str, *, model_name: str = DEFAULT_EMBEDDING_MODEL) -> list[float]:
    vecs = embed_texts([text], model_name=model_name, batch_size=1)
    return vecs[0] if vecs else []


if TYPE_CHECKING:
    pass
