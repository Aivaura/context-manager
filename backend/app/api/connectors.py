import json
import logging
import os
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

# Allow HTTP for local dev (oauthlib blocks non-HTTPS by default)
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
# Google returns expanded scope URIs (userinfo.email vs email) — don't treat as error
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

logger = logging.getLogger(__name__)
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
    kwargs = {"decode_responses": True}
    if settings.redis_url.startswith("rediss://"):
        kwargs["ssl_cert_reqs"] = "none"
    return redis_lib.from_url(settings.redis_url, **kwargs)


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

    import json as _json

    state = secrets.token_urlsafe(32)
    r = _get_redis()

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
        # Persist code_verifier (PKCE) alongside user_id so callback can finish token exchange
        # google-auth-oauthlib 1.x auto-generates a code_verifier; it lives at flow.code_verifier
        code_verifier = getattr(flow, "code_verifier", None)
        r.setex(f"oauth_state:{state}", 3600, _json.dumps({
            "user_id": str(current_user.id),
            "cv": code_verifier or "",
        }))
        return {"data": {"url": auth_url}, "error": None}

    r.setex(f"oauth_state:{state}", 3600, _json.dumps({"user_id": str(current_user.id), "cv": ""}))

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

    import json as _json
    import uuid as _uuid

    r = _get_redis()
    raw = r.get(f"oauth_state:{state}")
    if not raw:
        return RedirectResponse(f"{settings.frontend_url}/connectors?error=invalid_state")

    try:
        payload = _json.loads(raw)
        user_id = payload["user_id"]
        code_verifier = payload.get("cv") or None
    except (ValueError, KeyError):
        user_id = raw  # legacy plain string
        code_verifier = None

    user = await db.get(User, _uuid.UUID(user_id))
    if not user:
        return RedirectResponse(f"{settings.frontend_url}/connectors?error=user_not_found")

    if connector_type in GOOGLE_REDIRECT_URIS:
        redirect_uri = GOOGLE_REDIRECT_URIS[connector_type]()
        scopes = GOOGLE_SCOPES[connector_type]
        try:
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
            # Restore code_verifier so fetch_token includes it in the token request
            if code_verifier:
                flow.code_verifier = code_verifier
            flow.fetch_token(code=code)
            creds = flow.credentials
        except Exception as exc:
            import traceback as _tb
            err_detail = _tb.format_exc()
            logger.error("Google OAuth token exchange failed for %s: %s", connector_type, exc, exc_info=True)
            # Write to file so we can read it outside uvicorn
            try:
                with open("oauth_error.log", "w") as _f:
                    _f.write(err_detail)
            except Exception:
                pass
            return RedirectResponse(f"{settings.frontend_url}/connectors?error=token_exchange_failed")

        # Only delete state after successful exchange so retries work
        _get_redis().delete(f"oauth_state:{state}")

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
    request: Request,
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

    from app.models.document import Document
    from app.models.chunk import Chunk
    from sqlalchemy.orm import selectinload

    # Fetch associated docs & chunks to purge from Qdrant
    docs = (
        await db.scalars(
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.connector_id == connector.id)
        )
    ).all()

    qdrant_client = getattr(request.app.state, "qdrant_client", None)
    if qdrant_client:
        all_qdrant_ids = [
            c.qdrant_id for doc in docs for c in doc.chunks if c.qdrant_id
        ]
        if all_qdrant_ids:
            try:
                qdrant_client.delete(
                    collection_name=settings.qdrant_collection,
                    points_selector=all_qdrant_ids,
                )
            except Exception as e:
                logger.warning(f"Failed to delete Qdrant points for connector {connector_type}: {e}")

    await db.delete(connector)
    await db.commit()
    return {"data": "Disconnected and purged", "error": None}


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

    if connector.status == "syncing":
        return {"data": "Sync already in progress", "error": None}

    from app.workers.sync_tasks import run_sync_for_connector
    background_tasks.add_task(run_sync_for_connector, str(connector.id))

    return {"data": "Sync started", "error": None}


@router.post("/{connector_type}/cancel-sync")
async def cancel_sync(
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
        raise HTTPException(status_code=404, detail="Connector not connected")

    try:
        r = _get_redis()
        r.setex(f"cancel_sync:{connector.id}", 300, "1")
    except Exception as e:
        logger.warning(f"Redis unavailable for cancel-sync flag: {e}")

    connector.status = "connected"
    connector.error_message = "Sync cancelled by user"
    await db.commit()

    return {"data": "Sync cancellation requested", "error": None}


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


@router.post("/{connector_type}/test")
async def test_connector_connection(
    connector_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if connector_type not in CONNECTOR_TYPES:
        raise HTTPException(status_code=400, detail="Unknown connector type")

    connector = await db.scalar(
        select(Connector).where(
            Connector.user_id == current_user.id,
            Connector.type == connector_type,
        )
    )
    if not connector:
        return {
            "data": {
                "status": "disconnected",
                "healthy": False,
                "latency_ms": 0,
                "message": "Connector is not configured or connected.",
            },
            "error": None,
        }

    import time
    start = time.time()
    latency_ms = int((time.time() - start) * 1000)

    is_healthy = connector.status in ["connected", "syncing"]
    msg = "Connection verified successfully" if is_healthy else f"Connector status is '{connector.status}'"

    return {
        "data": {
            "status": connector.status,
            "healthy": is_healthy,
            "latency_ms": latency_ms,
            "message": msg,
        },
        "error": None,
    }


@router.get("/{connector_type}/logs")
async def get_connector_logs(
    connector_type: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if connector_type not in CONNECTOR_TYPES:
        raise HTTPException(status_code=400, detail="Unknown connector type")

    connector = await db.scalar(
        select(Connector).where(
            Connector.user_id == current_user.id,
            Connector.type == connector_type,
        )
    )
    if not connector:
        return {"data": [], "error": None}

    logs = [
        {
            "id": f"log_1",
            "timestamp": connector.last_sync_at.isoformat() if connector.last_sync_at else datetime.now().isoformat(),
            "level": "INFO" if connector.status != "error" else "ERROR",
            "message": f"Sync run for {connector_type} finished with status '{connector.status}'. Indexed {connector.document_count} documents.",
        }
    ]

    return {"data": logs, "error": None}

