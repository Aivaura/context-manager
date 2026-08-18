import base64
import json
from datetime import datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.connectors.base import BaseConnector, ConnectorStatus
from app.processing.pipeline import RawDocument

SCOPES_GMAIL = ["https://www.googleapis.com/auth/gmail.readonly"]
SKIP_LABELS = {"SPAM", "TRASH"}


import logging
import time
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)


def _execute_with_retry(request, max_retries=5, initial_delay=2.0):
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            return request.execute(num_retries=3)
        except HttpError as e:
            if e.resp.status in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                logger.warning(
                    f"Gmail API rate limit / error (HTTP {e.resp.status}). Retrying in {delay:.1f}s... (attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(delay)
                delay *= 2
            else:
                raise


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
        import asyncio
        from app.connectors.utils import decrypt_token
        token_dict = decrypt_token(connector_record.oauth_token_encrypted)
        return await asyncio.to_thread(self._fetch_documents_sync, token_dict, since)

    def _fetch_documents_sync(self, token_dict: dict, since: datetime | None) -> list[RawDocument]:
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

            req = service.users().messages().list(**kwargs)
            try:
                response = _execute_with_retry(req)
                messages.extend(response.get("messages", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break
            except Exception as e:
                logger.error(f"Failed to list Gmail messages: {e}")
                break

        results = []
        for idx, msg_ref in enumerate(messages):
            if idx > 0 and idx % 20 == 0:
                time.sleep(0.2)  # Pace requests to avoid spiking API quota

            try:
                get_req = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="full"
                )
                msg = _execute_with_retry(get_req)

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
            except Exception as exc:
                logger.warning(f"Failed to fetch Gmail message {msg_ref['id']}: {exc}")
                continue

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
