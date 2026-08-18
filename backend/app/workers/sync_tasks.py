import asyncio
import logging
from datetime import datetime

from app.config import get_settings
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_qdrant():
    from qdrant_client import QdrantClient
    from app.main import _sanitize_ascii
    return QdrantClient(
        url=settings.qdrant_url,
        api_key=_sanitize_ascii(settings.qdrant_api_key),
    )


async def run_sync_for_connector(connector_id: str, full_sync: bool = False):
    from app.database import AsyncSessionLocal
    from app.models.connector import Connector
    from app.models.sync_state import SyncState
    from app.processing.pipeline import process_document
    from sqlalchemy import select, update

    async with AsyncSessionLocal() as db:
        connector = await db.get(Connector, connector_id)
        if not connector:
            return

        await db.execute(
            update(Connector)
            .where(Connector.id == connector.id)
            .values(status="syncing", error_message=None)
        )
        await db.commit()

        try:
            since = None
            if not full_sync and connector.last_sync_at:
                since = connector.last_sync_at

            connector_impl = _get_connector_impl(connector.type)
            if not connector_impl:
                return

            docs = await connector_impl.fetch_documents(connector, since=since)
            qdrant_client = _get_qdrant()

            from app.api.connectors import _get_redis
            r_client = None
            try:
                r_client = _get_redis()
            except Exception:
                pass

            for raw_doc in docs:
                if r_client and r_client.get(f"cancel_sync:{connector_id}"):
                    logger.info(f"Sync cancelled by user for connector {connector_id}")
                    r_client.delete(f"cancel_sync:{connector_id}")
                    await db.execute(
                        update(Connector)
                        .where(Connector.id == connector.id)
                        .values(status="connected", error_message="Sync cancelled by user")
                    )
                    await db.commit()
                    return

                try:
                    await process_document(raw_doc, connector, db, qdrant_client)
                except Exception as e:
                    logger.error(f"Error processing document {raw_doc.source_id}: {e}")

            from app.models.document import Document
            from sqlalchemy import func
            true_count = await db.scalar(
                select(func.count()).select_from(Document).where(
                    Document.connector_id == connector.id
                )
            )
            await db.execute(
                update(Connector)
                .where(Connector.id == connector.id)
                .values(
                    status="connected",
                    last_sync_at=datetime.utcnow(),
                    error_message=None,
                    document_count=true_count or 0,
                )
            )
            await db.commit()

        except Exception as e:
            logger.error(f"Sync failed for connector {connector_id}: {e}")
            await db.execute(
                update(Connector)
                .where(Connector.id == connector.id)
                .values(status="error", error_message=str(e)[:500])
            )
            await db.commit()


def _get_connector_impl(connector_type: str):
    if connector_type == "google_drive":
        from app.connectors.google_drive import GoogleDriveConnector
        return GoogleDriveConnector()
    if connector_type == "gmail":
        from app.connectors.gmail import GmailConnector
        return GmailConnector()
    if connector_type == "outlook":
        from app.connectors.outlook import OutlookConnector
        return OutlookConnector()
    if connector_type == "sheets":
        from app.connectors.sheets import SheetsConnector
        return SheetsConnector()
    return None


@celery_app.task(name="app.workers.sync_tasks.sync_connector_by_type")
def sync_connector_by_type(connector_type: str):
    from app.database import AsyncSessionLocal
    from app.models.connector import Connector
    from sqlalchemy import select

    async def _run():
        async with AsyncSessionLocal() as db:
            connectors = (
                await db.scalars(
                    select(Connector).where(
                        Connector.type == connector_type,
                        Connector.status.in_(["connected", "error"]),
                    )
                )
            ).all()

            for connector in connectors:
                await run_sync_for_connector(str(connector.id))

    asyncio.get_event_loop().run_until_complete(_run())


@celery_app.task(name="app.workers.sync_tasks.refresh_bm25_index")
def refresh_bm25_index():
    pass
