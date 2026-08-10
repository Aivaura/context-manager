"""
MCP Server for Context Store.

Run: python -m app.mcp.server
Connects to: http://localhost:3001

Claude config (~/.claude/settings.json):
{
  "mcpServers": {
    "context-store": {
      "url": "http://localhost:3001"
    }
  }
}
"""

import asyncio
import os
import sys

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from app.config import get_settings

settings = get_settings()
mcp = FastMCP("context-store", port=3001)


def _get_qdrant():
    from qdrant_client import QdrantClient
    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)


@mcp.tool()
async def search_company_knowledge(query: str, top_k: int = 5) -> list[dict]:
    """Search the company knowledge base and return relevant chunks with citations."""
    from app.processing.embedder import embed_text
    from app.retrieval.reranker import rerank
    from app.retrieval.hybrid_search import HybridSearchEngine

    qdrant_client = _get_qdrant()
    engine = HybridSearchEngine(qdrant_client, settings.qdrant_collection)

    results = await engine.search(query, top_k=top_k * 4)
    top = rerank(query, results, top_k=top_k)

    return [
        {
            "text": r.text,
            "source_type": r.source_type,
            "document_title": r.document_title,
            "document_url": r.document_url,
            "author": r.author,
            "date": r.date,
            "score": r.score,
        }
        for r in top
    ]


@mcp.tool()
async def get_document(document_id: str) -> dict:
    """Retrieve a full document by its ID."""
    from app.database import AsyncSessionLocal
    from app.models.document import Document
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        import uuid
        doc = await db.scalar(select(Document).where(Document.id == uuid.UUID(document_id)))
        if not doc:
            return {"error": "Document not found"}

        await db.refresh(doc, attribute_names=["chunks"])
        text = " ".join(c.text for c in sorted(doc.chunks, key=lambda x: x.chunk_index))

        return {
            "id": str(doc.id),
            "title": doc.title,
            "source_url": doc.source_url,
            "author": doc.author,
            "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None,
            "text": text,
        }


@mcp.tool()
async def list_sources() -> list[dict]:
    """List all connected data sources with sync status and document counts."""
    from app.database import AsyncSessionLocal
    from app.models.connector import Connector
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        connectors = (await db.scalars(select(Connector))).all()
        return [
            {
                "type": c.type,
                "status": c.status,
                "document_count": c.document_count,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
            }
            for c in connectors
        ]


@mcp.tool()
async def get_recent_messages(source_type: str, limit: int = 20) -> list[dict]:
    """Get most recent documents from a specific source."""
    from app.database import AsyncSessionLocal
    from app.models.connector import Connector
    from app.models.document import Document
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        docs = (
            await db.scalars(
                select(Document)
                .join(Connector)
                .where(Connector.type == source_type)
                .order_by(Document.source_created_at.desc())
                .limit(limit)
            )
        ).all()

        return [
            {
                "id": str(d.id),
                "title": d.title,
                "author": d.author,
                "source_url": d.source_url,
                "date": d.source_created_at.isoformat() if d.source_created_at else None,
            }
            for d in docs
        ]


if __name__ == "__main__":
    mcp.run()
