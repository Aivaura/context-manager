import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import get_current_user
from app.database import get_db
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/query", tags=["query"])


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)


class SourceResponse(BaseModel):
    title: str
    url: str | None
    date: str | None
    author: str | None
    source_type: str
    snippet: str


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceResponse]
    query_id: str


@router.post("", response_model=QueryResponse)
async def query(
    body: QueryRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    search_engine = request.app.state.search_engine
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search engine not initialized")

    from app.retrieval.query_engine import run_query
    result = await run_query(
        question=body.question,
        search_engine=search_engine,
        top_k=body.top_k,
        db=db,
    )

    log = AuditLog(
        user_id=current_user.id,
        query_text=body.question,
        response_text=result.answer,
        sources_used=json.dumps([s["title"] for s in result.sources]),
    )
    db.add(log)
    await db.commit()

    return QueryResponse(
        answer=result.answer,
        sources=[SourceResponse(**s) for s in result.sources],
        query_id=result.query_id,
    )


@router.get("/history")
async def query_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    logs = (
        await db.scalars(
            select(AuditLog)
            .where(AuditLog.user_id == current_user.id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
    ).all()

    return {
        "data": [
            {
                "id": str(log.id),
                "query": log.query_text,
                "answer_preview": (log.response_text or "")[:150],
                "sources": json.loads(log.sources_used or "[]"),
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
        "error": None,
    }
