import json

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models.connector import Connector

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
settings = get_settings()


@router.get("/whatsapp")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        return int(challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def receive_whatsapp(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    body = await request.json()

    entry = body.get("entry", [{}])[0]
    changes = entry.get("changes", [{}])[0]
    value = changes.get("value", {})
    messages = value.get("messages", [])
    contacts = value.get("contacts", [])

    if not messages:
        return {"status": "ok"}

    connector = await db.scalar(
        select(Connector).where(Connector.type == "whatsapp", Connector.status == "connected")
    )
    if not connector:
        return {"status": "ok"}

    background_tasks.add_task(_process_whatsapp_messages, str(connector.id), messages, contacts)
    return {"status": "ok"}


async def _process_whatsapp_messages(connector_id: str, messages: list, contacts: list):
    from app.connectors.whatsapp import WhatsAppConnector
    from app.database import AsyncSessionLocal
    from app.processing.pipeline import process_document

    connector_obj = WhatsAppConnector()

    async with AsyncSessionLocal() as db:
        from app.models.connector import Connector
        connector = await db.get(Connector, connector_id)
        if not connector:
            return

        qdrant_client = _get_qdrant()
        for message in messages:
            raw_doc = connector_obj.process_webhook_message(message, contacts)
            if raw_doc:
                try:
                    await process_document(raw_doc, connector, db, qdrant_client)
                except Exception:
                    pass


def _get_qdrant():
    from qdrant_client import QdrantClient
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
    )
