import base64
import json
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.connectors.base import BaseConnector, ConnectorStatus
from app.processing.pipeline import RawDocument

SCOPES_GMAIL = ["https://www.googleapis.com/auth/gmail.readonly"]
SKIP_LABELS = {"SPAM", "TRASH"}


class GmailConnector(BaseConnector):
    async def authenticate(self, **kwargs) -> dict:
        return {}

    def _build_service(self, token_dict: dict):
        creds = Credentials(
            token=token_dict.get("access_token"),
            refresh_token=token_dict.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=token_dict.get("client_id"),
            client_secret=token_dict.get("client_secret"),
            scopes=SCOPES_GMAIL,
        )
        return build("gmail", "v1", credentials=creds)

    async def fetch_documents(self, connector_record, since: datetime | None = None) -> list[RawDocument]:
        from app.connectors.utils import decrypt_token
        token_dict = decrypt_token(connector_record.oauth_token_encrypted)
        service = self._build_service(token_dict)

        query = "-in:spam -in:trash"
        if since:
            epoch = int(since.timestamp())
            query += f" after:{epoch}"

        messages = []
        page_token = None

        while True:
            kwargs = {"userId": "me", "q": query, "maxResults": 500}
            if page_token:
                kwargs["pageToken"] = page_token

            response = service.users().messages().list(**kwargs).execute()
            messages.extend(response.get("messages", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        results = []
        for msg_ref in messages[:500]:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="full"
            ).execute()

            labels = msg.get("labelIds", [])
            if any(skip in labels for skip in SKIP_LABELS):
                continue

            text = _extract_gmail_body(msg)
            if not text.strip():
                continue

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            subject = headers.get("Subject", "(no subject)")
            sender = headers.get("From", "")
            date_str = headers.get("Date", "")
            thread_id = msg.get("threadId", msg["id"])

            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(date_str)
            except Exception:
                dt = None

            results.append(
                RawDocument(
                    source_id=thread_id,
                    title=f"Email: {subject}",
                    text=f"Subject: {subject}\nFrom: {sender}\n\n{text}",
                    author=sender,
                    source_url=None,
                    source_created_at=dt,
                    is_html=False,
                )
            )

        return results

    async def get_status(self, connector_record) -> ConnectorStatus:
        return ConnectorStatus(
            status=connector_record.status,
            last_sync_at=connector_record.last_sync_at,
            document_count=connector_record.document_count,
            error_message=connector_record.error_message,
        )


def _extract_gmail_body(msg: dict) -> str:
    payload = msg.get("payload", {})
    return _get_part_text(payload)


def _get_part_text(part: dict) -> str:
    mime = part.get("mimeType", "")
    body = part.get("body", {})
    data = body.get("data", "")

    if mime == "text/plain" and data:
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")

    if mime == "text/html" and data:
        from app.processing.cleaner import clean_html
        raw = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="ignore")
        return clean_html(raw)

    parts = part.get("parts", [])
    for sub_part in parts:
        text = _get_part_text(sub_part)
        if text:
            return text

    return ""
