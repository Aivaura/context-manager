import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.chunk import Chunk as ChunkModel
from app.models.connector import Connector
from app.models.document import Document
from app.processing.chunker import chunk_text
from app.processing.cleaner import clean_document
from app.processing.embedder import embed_text

settings = get_settings()


@dataclass
class RawDocument:
    source_id: str
    title: str
    text: str
    author: str | None = None
    source_url: str | None = None
    source_created_at: datetime | None = None
    is_html: bool = False
    source_type: str = "text"


async def process_document(
    raw: RawDocument,
    connector: Connector,
    db: AsyncSession,
    qdrant_client,
) -> Document:
    from sqlalchemy.orm import selectinload

    existing = await db.scalar(
        select(Document)
        .options(selectinload(Document.chunks))
        .where(
            Document.connector_id == connector.id,
            Document.source_id == raw.source_id,
        )
    )

    cleaned = clean_document(raw.text, is_html=raw.is_html)
    chunks = chunk_text(cleaned, source_type=raw.source_type)

    if existing:
        for chunk_model in existing.chunks:
            if chunk_model.qdrant_id:
                try:
                    qdrant_client.delete(
                        collection_name=settings.qdrant_collection,
                        points_selector=[chunk_model.qdrant_id],
                    )
                except Exception:
                    pass
        await db.delete(existing)
        await db.flush()

    doc = Document(
        connector_id=connector.id,
        source_id=raw.source_id,
        source_url=raw.source_url,
        title=raw.title,
        author=raw.author,
        source_created_at=raw.source_created_at,
        indexed_at=datetime.utcnow(),
        chunk_count=len(chunks),
    )
    db.add(doc)
    await db.flush()

    from qdrant_client.models import PointStruct

    points = []
    chunk_models = []

    for chunk in chunks:
        embedding = await embed_text(chunk.text)
        qdrant_id = str(uuid.uuid4())

        payload = {
            "chunk_id": qdrant_id,
            "document_id": str(doc.id),
            "source_type": connector.type,
            "source_name": connector.type,
            "document_title": raw.title or "",
            "document_url": raw.source_url or "",
            "author": raw.author or "",
            "date": raw.source_created_at.isoformat() if raw.source_created_at else "",
            "text": chunk.text,
            "chunk_index": chunk.chunk_index,
        }

        points.append(PointStruct(id=qdrant_id, vector=embedding, payload=payload))

        chunk_models.append(
            ChunkModel(
                document_id=doc.id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
                token_count=chunk.token_count,
                qdrant_id=qdrant_id,
            )
        )

    if points and qdrant_client:
        try:
            qdrant_client.upsert(
                collection_name=settings.qdrant_collection,
                points=points,
            )
        except Exception:
            pass

    db.add_all(chunk_models)

    await db.commit()
    return doc
