import json
from datetime import datetime

import httpx

from app.connectors.base import BaseConnector, ConnectorStatus
from app.processing.pipeline import RawDocument

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
SKIP_FOLDERS = {"Junk Email", "Deleted Items", "Drafts"}


class OutlookConnector(BaseConnector):
    async def authenticate(self, **kwargs) -> dict:
        return {}

    async def fetch_documents(self, connector_record, since: datetime | None = None) -> list[RawDocument]:
        from app.connectors.utils import decrypt_token, refresh_microsoft_token
        token_dict = decrypt_token(connector_record.oauth_token_encrypted)

        token_dict = await refresh_microsoft_token(token_dict)

        access_token = token_dict["access_token"]
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        filter_query = "isDraft eq false"
        if since:
            since_str = since.strftime("%Y-%m-%dT%H:%M:%SZ")
            filter_query += f" and receivedDateTime ge {since_str}"

        url = (
            f"{GRAPH_BASE}/me/messages"
            f"?$select=id,subject,from,receivedDateTime,body,conversationId"
            f"&$filter={filter_query}"
            f"&$top=100"
            f"&$orderby=receivedDateTime desc"
        )

        results = []
        async with httpx.AsyncClient(timeout=30.0) as client:
            while url:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                messages = data.get("value", [])

                for msg in messages:
                    body_content = msg.get("body", {}).get("content", "")
                    body_type = msg.get("body", {}).get("contentType", "text")
                    is_html = body_type == "html"

                    from app.processing.cleaner import clean_document
                    text = clean_document(body_content, is_html=is_html)
                    if not text.strip():
                        continue

                    sender = msg.get("from", {}).get("emailAddress", {}).get("address", "")
                    subject = msg.get("subject", "(no subject)")
                    received = msg.get("receivedDateTime")
                    dt = datetime.fromisoformat(received.replace("Z", "+00:00")) if received else None

                    results.append(
                        RawDocument(
                            source_id=msg.get("conversationId", msg["id"]),
                            title=f"Email: {subject}",
                            text=f"Subject: {subject}\nFrom: {sender}\n\n{text}",
                            author=sender,
                            source_url=None,
                            source_created_at=dt,
                            is_html=False,
                        )
                    )

                url = data.get("@odata.nextLink")
                if len(results) >= 500:
                    break

        return results

    async def get_status(self, connector_record) -> ConnectorStatus:
        return ConnectorStatus(
            status=connector_record.status,
            last_sync_at=connector_record.last_sync_at,
            document_count=connector_record.document_count,
            error_message=connector_record.error_message,
        )
