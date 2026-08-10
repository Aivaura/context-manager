from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.connector import Connector
from app.models.document import Document
from app.models.user import User

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    logs = (
        await db.scalars(
            select(AuditLog)
            .order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).all()

    return {
        "data": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id),
                "query": log.query_text,
                "answer_preview": (log.response_text or "")[:200],
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "error": None,
    }


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    total_docs = await db.scalar(
        select(func.count()).select_from(Document).join(Connector).where(Connector.user_id == current_user.id)
    )
    total_queries = await db.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.user_id == current_user.id)
    )
    active_connectors = await db.scalar(
        select(func.count()).select_from(Connector).where(
            Connector.user_id == current_user.id,
            Connector.status == "connected",
        )
    )

    return {
        "data": {
            "total_documents": total_docs or 0,
            "total_queries": total_queries or 0,
            "active_connectors": active_connectors or 0,
        },
        "error": None,
    }


@router.post("/reindex")
async def trigger_reindex(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    connectors = (
        await db.scalars(
            select(Connector).where(
                Connector.user_id == current_user.id,
                Connector.status == "connected",
            )
        )
    ).all()

    from app.workers.sync_tasks import run_sync_for_connector
    for connector in connectors:
        background_tasks.add_task(run_sync_for_connector, str(connector.id), full_sync=True)

    return {"data": f"Reindex started for {len(connectors)} connectors", "error": None}
