import asyncio
from collections import defaultdict
from dataclasses import dataclass, field

from rank_bm25 import BM25Okapi

from app.processing.embedder import embed_text


@dataclass
class SearchResult:
    chunk_id: str
    document_id: str
    text: str
    source_type: str
    source_name: str
    document_title: str
    document_url: str
    author: str
    date: str
    chunk_index: int
    score: float = 0.0


class HybridSearchEngine:
    def __init__(self, qdrant_client, collection_name: str):
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name
        self._bm25_index: BM25Okapi | None = None
        self._bm25_docs: list[dict] = []

    def refresh_bm25(self, chunks: list[dict]) -> None:
        if not chunks:
            return
        self._bm25_docs = chunks
        tokenized = [doc["text"].lower().split() for doc in chunks]
        self._bm25_index = BM25Okapi(tokenized)

    async def search(self, query: str, top_k: int = 5, filters: dict | None = None) -> list[SearchResult]:
        query_embedding = await embed_text(query)

        dense_results = await self._dense_search(query_embedding, top_k=25, filters=filters)
        sparse_results = self._sparse_search(query, top_k=25, filters=filters)

        merged = self._reciprocal_rank_fusion(dense_results, sparse_results)
        return merged[:30]

    async def _dense_search(self, embedding: list[float], top_k: int, filters: dict | None = None) -> list[SearchResult]:
        qdrant_filter = None
        if filters and filters.get("source_type"):
            from qdrant_client.models import FieldCondition, Filter, MatchValue
            stype = filters["source_type"]
            qdrant_filter = Filter(
                must=[
                    FieldCondition(
                        key="source_type",
                        match=MatchValue(value=stype),
                    )
                ]
            )

        kwargs = {
            "collection_name": self.collection_name,
            "query": embedding,
            "limit": top_k,
        }
        if qdrant_filter:
            kwargs["query_filter"] = qdrant_filter

        response = self.qdrant_client.query_points(**kwargs)
        results = []
        for hit in response.points:
            p = hit.payload or {}
            results.append(
                SearchResult(
                    chunk_id=p.get("chunk_id", str(hit.id)),
                    document_id=p.get("document_id", ""),
                    text=p.get("text", ""),
                    source_type=p.get("source_type", ""),
                    source_name=p.get("source_name", ""),
                    document_title=p.get("document_title", ""),
                    document_url=p.get("document_url", ""),
                    author=p.get("author", ""),
                    date=p.get("date", ""),
                    chunk_index=p.get("chunk_index", 0),
                    score=hit.score,
                )
            )
        return results

    def _sparse_search(self, query: str, top_k: int, filters: dict | None = None) -> list[SearchResult]:
        if self._bm25_index is None or not self._bm25_docs:
            return []

        tokens = query.lower().split()
        scores = self._bm25_index.get_scores(tokens)

        target_source = filters.get("source_type") if filters else None

        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in ranked:
            if score > 0 and idx < len(self._bm25_docs):
                doc = self._bm25_docs[idx]
                if target_source and doc.get("source_type") != target_source:
                    continue
                results.append(
                    SearchResult(
                        chunk_id=doc.get("chunk_id", ""),
                        document_id=doc.get("document_id", ""),
                        text=doc.get("text", ""),
                        source_type=doc.get("source_type", ""),
                        source_name=doc.get("source_name", ""),
                        document_title=doc.get("document_title", ""),
                        document_url=doc.get("document_url", ""),
                        author=doc.get("author", ""),
                        date=doc.get("date", ""),
                        chunk_index=doc.get("chunk_index", 0),
                        score=float(score),
                    )
                )
                if len(results) >= top_k:
                    break
        return results

    @staticmethod
    def _reciprocal_rank_fusion(
        list_a: list[SearchResult],
        list_b: list[SearchResult],
        k: int = 60,
    ) -> list[SearchResult]:
        scores: dict[str, float] = defaultdict(float)
        by_id: dict[str, SearchResult] = {}

        for rank, result in enumerate(list_a):
            scores[result.chunk_id] += 1.0 / (k + rank + 1)
            by_id[result.chunk_id] = result

        for rank, result in enumerate(list_b):
            scores[result.chunk_id] += 1.0 / (k + rank + 1)
            if result.chunk_id not in by_id:
                by_id[result.chunk_id] = result

        sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)
        merged = []
        for cid in sorted_ids:
            r = by_id[cid]
            r.score = scores[cid]
            merged.append(r)

        return merged
