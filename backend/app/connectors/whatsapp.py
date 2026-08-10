import json
from datetime import datetime, timezone

from app.connectors.base import BaseConnector, ConnectorStatus
from app.processing.pipeline import RawDocument


class WhatsAppConnector(BaseConnector):
    async def authenticate(self, **kwargs) -> dict:
        return {}

    async def fetch_documents(self, connector_record, since: datetime | None = None) -> list[RawDocument]:
        return []

    def process_webhook_message(self, message: dict, contacts: list[dict]) -> RawDocument | None:
        msg_type = message.get("type")
        if msg_type not in ("text", "audio"):
            return None

        contact_name = ""
        sender_id = message.get("from", "")
        for contact in contacts:
            if contact.get("wa_id") == sender_id:
                contact_name = contact.get("profile", {}).get("name", sender_id)
                break
        if not contact_name:
            contact_name = sender_id

        timestamp = int(message.get("timestamp", 0))
        dt = datetime.fromtimestamp(timestamp, tz=timezone.utc) if timestamp else datetime.now(tz=timezone.utc)

        if msg_type == "text":
            text = message.get("text", {}).get("body", "")
            if not text.strip():
                return None
        else:
            text = "[Voice note — transcription not available]"

        date_key = dt.strftime("%Y-%m-%d")
        source_id = f"wa_{sender_id}_{date_key}"

        return RawDocument(
            source_id=source_id,
            title=f"WhatsApp: {contact_name} ({date_key})",
            text=f"[{dt.strftime('%H:%M')}] {contact_name}: {text}",
            author=contact_name,
            source_url=None,
            source_created_at=dt,
            source_type="whatsapp",
        )

    async def get_status(self, connector_record) -> ConnectorStatus:
        return ConnectorStatus(
            status=connector_record.status,
            last_sync_at=connector_record.last_sync_at,
            document_count=connector_record.document_count,
            error_message=connector_record.error_message,
        )
