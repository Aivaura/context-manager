from functools import lru_cache

from app.retrieval.hybrid_search import SearchResult


@lru_cache(maxsize=1)
def _load_cross_encoder():
    from sentence_transformers import CrossEncoder
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(query: str, results: list[SearchResult], top_k: int = 8) -> list[SearchResult]:
    if not results:
        return []

    try:
        model = _load_cross_encoder()
        pairs = [(query, r.text) for r in results]
        scores = model.predict(pairs)

        for i, result in enumerate(results):
            result.score = float(scores[i])

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]
    except Exception:
        return results[:top_k]
