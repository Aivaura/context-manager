import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models.connector import Connector
from app.models.note import Note
from app.models.user import User

router = APIRouter(prefix="/notes", tags=["notes"])
settings = get_settings()


class NoteCreate(BaseModel):
    title: str
    content: str
    tags: list[str] = []


class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    tags: list[str] | None = None


def extract_wiki_links(text: str) -> list[str]:
    pattern = r"\[\[(.*?)\]\]"
    return re.findall(pattern, text)


async def get_or_create_notes_connector(user_id: uuid.UUID, db: AsyncSession) -> Connector:
    stmt = select(Connector).where(Connector.user_id == user_id, Connector.type == "notes")
    connector = await db.scalar(stmt)
    if not connector:
        connector = Connector(
            user_id=user_id,
            type="notes",
            status="connected",
        )
        db.add(connector)
        await db.flush()
    return connector


@router.get("")
async def list_notes(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Note).where(Note.user_id == current_user.id).order_by(Note.updated_at.desc())
    notes = (await db.scalars(stmt)).all()
    return {
        "data": [
            {
                "id": str(n.id),
                "title": n.title,
                "content": n.content,
                "tags": n.tags or [],
                "linked_doc_ids": n.linked_doc_ids or [],
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "updated_at": n.updated_at.isoformat() if n.updated_at else None,
            }
            for n in notes
        ],
        "error": None,
    }


@router.post("")
async def create_note(
    payload: NoteCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    title = payload.title.strip() or "Untitled Note"
    content = payload.content
    wiki_links = extract_wiki_links(content)

    note = Note(
        user_id=current_user.id,
        title=title,
        content=content,
        tags=payload.tags,
        linked_doc_ids=wiki_links,
    )
    db.add(note)
    await db.flush()

    connector = await get_or_create_notes_connector(current_user.id, db)
    qdrant_client = getattr(request.app.state, "qdrant_client", None)

    from app.processing.pipeline import RawDocument, process_document
    raw_doc = RawDocument(
        source_id=f"note_{note.id}",
        title=f"Note: {title}",
        text=content if content.strip() else title,
        author=current_user.email,
        source_url=f"/notes/{note.id}",
    )
    await process_document(raw_doc, connector, db, qdrant_client)

    return {
        "data": {
            "id": str(note.id),
            "title": note.title,
            "content": note.content,
            "tags": note.tags or [],
            "linked_doc_ids": note.linked_doc_ids or [],
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        },
        "error": None,
    }


@router.get("/{note_id}")
async def get_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        nid = uuid.UUID(note_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid note ID")

    note = await db.scalar(select(Note).where(Note.id == nid, Note.user_id == current_user.id))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    return {
        "data": {
            "id": str(note.id),
            "title": note.title,
            "content": note.content,
            "tags": note.tags or [],
            "linked_doc_ids": note.linked_doc_ids or [],
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        },
        "error": None,
    }


@router.put("/{note_id}")
async def update_note(
    note_id: str,
    payload: NoteUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        nid = uuid.UUID(note_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid note ID")

    note = await db.scalar(select(Note).where(Note.id == nid, Note.user_id == current_user.id))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    if payload.title is not None:
        note.title = payload.title.strip() or note.title
    if payload.content is not None:
        note.content = payload.content
        note.linked_doc_ids = extract_wiki_links(payload.content)
    if payload.tags is not None:
        note.tags = payload.tags

    await db.flush()

    connector = await get_or_create_notes_connector(current_user.id, db)
    qdrant_client = getattr(request.app.state, "qdrant_client", None)

    from app.processing.pipeline import RawDocument, process_document
    raw_doc = RawDocument(
        source_id=f"note_{note.id}",
        title=f"Note: {note.title}",
        text=note.content if note.content.strip() else note.title,
        author=current_user.email,
        source_url=f"/notes/{note.id}",
    )
    await process_document(raw_doc, connector, db, qdrant_client)

    return {
        "data": {
            "id": str(note.id),
            "title": note.title,
            "content": note.content,
            "tags": note.tags or [],
            "linked_doc_ids": note.linked_doc_ids or [],
            "created_at": note.created_at.isoformat() if note.created_at else None,
            "updated_at": note.updated_at.isoformat() if note.updated_at else None,
        },
        "error": None,
    }


@router.delete("/{note_id}")
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        nid = uuid.UUID(note_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid note ID")

    note = await db.scalar(select(Note).where(Note.id == nid, Note.user_id == current_user.id))
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    await db.delete(note)
    await db.commit()
    return {"data": "Note deleted successfully", "error": None}
