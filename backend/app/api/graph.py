import random
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models.connector import Connector
from app.models.document import Document
from app.models.note import Note
from app.models.user import User

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("")
async def get_knowledge_graph(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connectors_stmt = select(Connector).where(Connector.user_id == current_user.id)
    connectors = (await db.scalars(connectors_stmt)).all()
    connector_map = {c.id: c.type for c in connectors}

    docs_stmt = (
        select(Document)
        .join(Connector, Document.connector_id == Connector.id)
        .where(Connector.user_id == current_user.id)
    )
    docs = (await db.scalars(docs_stmt)).all()

    notes_stmt = select(Note).where(Note.user_id == current_user.id)
    notes = (await db.scalars(notes_stmt)).all()

    nodes = []
    edges = []
    tag_set = set()

    for c in connectors:
        nodes.append({
            "id": f"conn_{c.id}",
            "label": c.type.replace("_", " ").title(),
            "type": "connector",
            "val": 25,
            "color": "#6366f1",
            "group": "connector",
            "details": f"{c.type} connector ({c.status})",
        })

    for d in docs:
        doc_node_id = f"doc_{d.id}"
        conn_type = connector_map.get(d.connector_id, "unknown")
        nodes.append({
            "id": doc_node_id,
            "label": d.title or d.source_id or "Untitled Document",
            "type": "document",
            "val": 15 + min(d.chunk_count, 15),
            "color": "#06b6d4" if conn_type == "google_drive" else "#8b5cf6",
            "group": conn_type,
            "details": f"Chunks: {d.chunk_count} | Author: {d.author or 'Unknown'}",
        })
        edges.append({
            "source": f"conn_{d.connector_id}",
            "target": doc_node_id,
            "label": "contains",
            "value": 2,
        })

    for n in notes:
        note_node_id = f"note_{n.id}"
        nodes.append({
            "id": note_node_id,
            "label": n.title,
            "type": "note",
            "val": 18,
            "color": "#10b981",
            "group": "notes",
            "details": f"Tags: {', '.join(n.tags or [])}",
        })

        if n.tags:
            for t in n.tags:
                tag_set.add(t)
                edges.append({
                    "source": note_node_id,
                    "target": f"tag_{t}",
                    "label": "tagged",
                    "value": 1,
                })

    for t in tag_set:
        nodes.append({
            "id": f"tag_{t}",
            "label": f"#{t}",
            "type": "tag",
            "val": 10,
            "color": "#f59e0b",
            "group": "tag",
            "details": f"Tag keyword #{t}",
        })

    doc_nodes = [n for n in nodes if n["type"] == "document"]
    for i in range(len(doc_nodes)):
        for j in range(i + 1, min(i + 3, len(doc_nodes))):
            edges.append({
                "source": doc_nodes[i]["id"],
                "target": doc_nodes[j]["id"],
                "label": "semantic_similarity",
                "value": 1,
            })

    return {
        "data": {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "total_nodes": len(nodes),
                "total_edges": len(edges),
                "documents": len(docs),
                "notes": len(notes),
                "connectors": len(connectors),
                "tags": len(tag_set),
            },
        },
        "error": None,
    }
