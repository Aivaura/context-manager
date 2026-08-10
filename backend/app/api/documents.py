from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.connector import Connector
from app.models.document import Document
from app.models.user import User

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


@router.get("")
async def list_documents(
    connector: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Document)
        .join(Connector, Document.connector_id == Connector.id)
        .where(Connector.user_id == current_user.id)
        .order_by(Document.indexed_at.desc())
    )

    if connector:
        stmt = stmt.where(Connector.type == connector)

    stmt = stmt.offset(offset).limit(limit)
    docs = (await db.scalars(stmt)).all()

    return {
        "data": [
            {
                "id": str(d.id),
                "title": d.title,
                "source_url": d.source_url,
                "author": d.author,
                "chunk_count": d.chunk_count,
                "indexed_at": d.indexed_at.isoformat() if d.indexed_at else None,
                "source_id": d.source_id,
            }
            for d in docs
        ],
        "error": None,
    }


@router.get("/{doc_id}")
async def get_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        uid = _uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    doc = await db.scalar(
        select(Document)
        .join(Connector)
        .where(Document.id == uid, Connector.user_id == current_user.id)
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.refresh(doc, attribute_names=["chunks"])
    full_text = " ".join(c.text for c in sorted(doc.chunks, key=lambda x: x.chunk_index))

    return {
        "data": {
            "id": str(doc.id),
            "title": doc.title,
            "source_url": doc.source_url,
            "author": doc.author,
            "text": full_text,
            "chunk_count": doc.chunk_count,
            "indexed_at": doc.indexed_at.isoformat() if doc.indexed_at else None,
        },
        "error": None,
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    import uuid as _uuid
    try:
        uid = _uuid.UUID(doc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid document ID")

    doc = await db.scalar(
        select(Document)
        .join(Connector)
        .where(Document.id == uid, Connector.user_id == current_user.id)
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await db.refresh(doc, attribute_names=["chunks"])
    qdrant_client = request.app.state.qdrant_client
    if qdrant_client:
        qdrant_ids = [c.qdrant_id for c in doc.chunks if c.qdrant_id]
        if qdrant_ids:
            try:
                qdrant_client.delete(
                    collection_name=settings.qdrant_collection,
                    points_selector=qdrant_ids,
                )
            except Exception:
                pass

    await db.delete(doc)
    await db.commit()
    return {"data": "Document deleted", "error": None}


@router.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filename = file.filename or "upload"
    if not (filename.endswith(".xlsx") or filename.endswith(".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported")

    data = await file.read()

    connector = await db.scalar(
        select(Connector).where(
            Connector.user_id == current_user.id,
            Connector.type == "sheets",
        )
    )
    if not connector:
        connector = Connector(
            user_id=current_user.id,
            type="sheets",
            status="connected",
        )
        db.add(connector)
        await db.flush()

    from app.connectors.sheets import process_excel_file
    raw_docs = process_excel_file(filename, data)

    qdrant_client = request.app.state.qdrant_client
    from app.processing.pipeline import process_document

    processed = 0
    for raw_doc in raw_docs:
        try:
            await process_document(raw_doc, connector, db, qdrant_client)
            processed += 1
        except Exception:
            pass

    return {"data": f"Uploaded and indexed {processed} sheet(s) from {filename}", "error": None}
