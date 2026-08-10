import json
import re
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.llm.factory import get_llm
from app.retrieval.hybrid_search import HybridSearchEngine, SearchResult
from app.retrieval.reranker import rerank

SYSTEM_PROMPT = """You are a company knowledge assistant. Answer questions using ONLY the context provided below.

Rules:
1. Answer ONLY from the provided context. Do not use outside knowledge.
2. Always cite your sources using [Source N] notation.
3. If the context does not contain enough information to answer, respond exactly with: "I do not have enough information in the indexed data to answer this."
4. Be concise and factual. Do not speculate or make up information.
5. If multiple sources support an answer, cite all of them.

Context:
{context}"""


@dataclass
class QueryResponse:
    answer: str
    sources: list[dict]
    query_id: str


def _extract_date_filter(query: str) -> tuple[str, dict | None]:
    filters = None
    patterns = [
        (r"\blast month\b", "last_month"),
        (r"\bthis month\b", "this_month"),
        (r"\blast week\b", "last_week"),
        (r"\bthis week\b", "this_week"),
        (r"\byesterday\b", "yesterday"),
        (r"\btoday\b", "today"),
    ]
    for pattern, period in patterns:
        if re.search(pattern, query, re.IGNORECASE):
            filters = {"date_period": period}
            break
    return query, filters


async def run_query(
    question: str,
    search_engine: HybridSearchEngine,
    top_k: int = 5,
    db: AsyncSession | None = None,
) -> QueryResponse:
    import uuid

    clean_question, date_filter = _extract_date_filter(question)

    candidates = await search_engine.search(clean_question, top_k=20, filters=date_filter)

    if not candidates:
        return QueryResponse(
            answer="I do not have enough information in the indexed data to answer this.",
            sources=[],
            query_id=str(uuid.uuid4()),
        )

    top_results = rerank(clean_question, candidates, top_k=max(top_k, 5))

    context_parts = []
    for i, result in enumerate(top_results, start=1):
        source_label = f"[Source {i}: {result.source_type.title()}"
        if result.author:
            source_label += f", From: {result.author}"
        if result.date:
            try:
                dt = datetime.fromisoformat(result.date)
                source_label += f", Date: {dt.strftime('%d %b %Y')}"
            except ValueError:
                source_label += f", Date: {result.date}"
        source_label += "]"
        context_parts.append(f"{source_label}\n{result.text}")

    context = "\n\n".join(context_parts)
    system = SYSTEM_PROMPT.format(context=context)

    llm = get_llm()
    answer = await llm.complete_with_system(system=system, user=clean_question)

    sources = []
    for i, result in enumerate(top_results, start=1):
        sources.append(
            {
                "index": i,
                "title": result.document_title or result.source_name,
                "url": result.document_url,
                "date": result.date,
                "author": result.author,
                "source_type": result.source_type,
                "snippet": result.text[:200] + "..." if len(result.text) > 200 else result.text,
            }
        )

    return QueryResponse(
        answer=answer,
        sources=sources,
        query_id=str(uuid.uuid4()),
    )
