import json
import secrets
from datetime import datetime
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.config import get_settings
from app.connectors.utils import decrypt_token, encrypt_token
from app.database import get_db
from app.models.connector import Connector
from app.models.user import User

router = APIRouter(prefix="/connectors", tags=["connectors"])
settings = get_settings()

GOOGLE_SCOPES = {
    "google_drive": [
        "https://www.googleapis.com/auth/drive.readonly",
        "openid",
        "email",
    ],
    "gmail": [
        "https://www.googleapis.com/auth/gmail.readonly",
        "openid",
        "email",
    ],
    "sheets": [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly",
        "openid",
        "email",
    ],
}

GOOGLE_REDIRECT_URIS = {
    "google_drive": lambda: settings.google_redirect_uri_drive,
    "gmail": lambda: settings.google_redirect_uri_gmail,
    "sheets": lambda: settings.google_redirect_uri_sheets,
}

CONNECTOR_TYPES = ["google_drive", "gmail", "outlook", "whatsapp", "sheets"]


class ConnectorStatusResponse(BaseModel):
    type: str
    status: str
    last_sync_at: datetime | None
    document_count: int
    error_message: str | None


def _get_redis():
    import redis as redis_lib
    return redis_lib.from_url(
        settings.redis_url,
        decode_responses=True,
        ssl_cert_reqs=None if settings.redis_url.startswith("rediss://") else None,
    )


@router.get("")
async def list_connectors(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connectors = (await db.scalars(
        select(Connector).where(Connector.user_id == current_user.id)
    )).all()

    by_type = {c.type: c for c in connectors}
    result = []
    for ctype in CONNECTOR_TYPES:
        if ctype in by_type:
            c = by_type[ctype]
            result.append({
                "type": c.type,
                "status": c.status,
                "last_sync_at": c.last_sync_at.isoformat() if c.last_sync_at else None,
                "document_count": c.document_count,
                "error_message": c.error_message,
            })
        else:
            result.append({
                "type": ctype,
                "status": "disconnected",
                "last_sync_at": None,
                "document_count": 0,
                "error_message": None,
            })

    return {"data": result, "error": None}


@router.get("/{connector_type}/auth-url")
async def get_auth_url(
    connector_type: str,
    current_user: User = Depends(get_current_user),
):
    if connector_type not in CONNECTOR_TYPES:
        raise HTTPException(status_code=400, detail="Unknown connector type")

    state = secrets.token_urlsafe(32)
    r = _get_redis()
    r.setex(f"oauth_state:{state}", 600, str(current_user.id))

    if connector_type in GOOGLE_REDIRECT_URIS:
        scopes = GOOGLE_SCOPES[connector_type]
        redirect_uri = GOOGLE_REDIRECT_URIS[connector_type]()
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uris": [redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=scopes,
        )
        flow.redirect_uri = redirect_uri
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            state=state,
            prompt="consent",
        )
        return {"data": {"url": auth_url}, "error": None}

    if connector_type == "outlook":
        params = {
            "client_id": settings.microsoft_client_id,
            "response_type": "code",
            "redirect_uri": settings.microsoft_redirect_uri,
            "scope": "https://graph.microsoft.com/Mail.Read offline_access",
            "state": state,
            "response_mode": "query",
        }
        auth_url = (
            f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}"
            f"/oauth2/v2.0/authorize?{urlencode(params)}"
        )
        return {"data": {"url": auth_url}, "error": None}

    if connector_type == "whatsapp":
        return {
            "data": {
                "message": "WhatsApp uses webhook-based connection. Configure your Meta app webhook to point to your backend URL.",
                "webhook_url": f"{settings.backend_url}/api/v1/webhooks/whatsapp",
                "verify_token": settings.whatsapp_verify_token,
            },
            "error": None,
        }

    raise HTTPException(status_code=400, detail="Auth flow not implemented for this connector")


@router.get("/{connector_type}/callback")
async def oauth_callback(
    connector_type: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get("error")

    if error:
        return RedirectResponse(f"{settings.frontend_url}/connectors?error={error}")

    if not code or not state:
        return RedirectResponse(f"{settings.frontend_url}/connectors?error=missing_params")

    r = _get_redis()
    user_id = r.get(f"oauth_state:{state}")
    if not user_id:
        return RedirectResponse(f"{settings.frontend_url}/connectors?error=invalid_state")
    r.delete(f"oauth_state:{state}")

    import uuid as _uuid
    user = await db.get(User, _uuid.UUID(user_id))
    if not user:
        return RedirectResponse(f"{settings.frontend_url}/connectors?error=user_not_found")

    if connector_type in GOOGLE_REDIRECT_URIS:
        redirect_uri = GOOGLE_REDIRECT_URIS[connector_type]()
        scopes = GOOGLE_SCOPES[connector_type]
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uris": [redirect_uri],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=scopes,
            state=state,
        )
        flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)
        creds = flow.credentials

        token_dict = {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
        }

    elif connector_type == "outlook":
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/token",
                data={
                    "client_id": settings.microsoft_client_id,
                    "client_secret": settings.microsoft_client_secret,
                    "code": code,
                    "redirect_uri": settings.microsoft_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code != 200:
                return RedirectResponse(f"{settings.frontend_url}/connectors?error=token_exchange_failed")
            token_dict = resp.json()
    else:
        return RedirectResponse(f"{settings.frontend_url}/connectors?error=unsupported")

    encrypted = encrypt_token(token_dict)

    existing = await db.scalar(
        select(Connector).where(
            Connector.user_id == user.id,
            Connector.type == connector_type,
        )
    )

    if existing:
        existing.oauth_token_encrypted = encrypted
        existing.status = "connected"
        existing.error_message = None
    else:
        connector = Connector(
            user_id=user.id,
            type=connector_type,
            status="connected",
            oauth_token_encrypted=encrypted,
        )
        db.add(connector)

    await db.commit()
    return RedirectResponse(f"{settings.frontend_url}/connectors?connected={connector_type}")


@router.delete("/{connector_type}")
async def disconnect_connector(
    connector_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connector = await db.scalar(
        select(Connector).where(
            Connector.user_id == current_user.id,
            Connector.type == connector_type,
        )
    )
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not found")

    await db.delete(connector)
    await db.commit()
    return {"data": "Disconnected", "error": None}


@router.post("/{connector_type}/sync")
async def trigger_sync(
    connector_type: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connector = await db.scalar(
        select(Connector).where(
            Connector.user_id == current_user.id,
            Connector.type == connector_type,
        )
    )
    if not connector:
        raise HTTPException(status_code=404, detail="Connector not connected")

    from app.workers.sync_tasks import run_sync_for_connector
    background_tasks.add_task(run_sync_for_connector, str(connector.id))

    return {"data": "Sync started", "error": None}


@router.get("/{connector_type}/status")
async def get_connector_status(
    connector_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connector = await db.scalar(
        select(Connector).where(
            Connector.user_id == current_user.id,
            Connector.type == connector_type,
        )
    )
    if not connector:
        return {
            "data": {
                "type": connector_type,
                "status": "disconnected",
                "last_sync_at": None,
                "document_count": 0,
                "error_message": None,
            },
            "error": None,
        }

    return {
        "data": {
            "type": connector.type,
            "status": connector.status,
            "last_sync_at": connector.last_sync_at.isoformat() if connector.last_sync_at else None,
            "document_count": connector.document_count,
            "error_message": connector.error_message,
        },
        "error": None,
    }
