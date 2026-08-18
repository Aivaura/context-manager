import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import get_settings
from app.database import engine, Base

logger = logging.getLogger(__name__)
settings = get_settings()


def _rate_key(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:20]
    return get_remote_address(request)


limiter = Limiter(key_func=_rate_key)


def _sanitize_ascii(value: str) -> str | None:
    """Strip non-ASCII characters from a string (e.g. bullet-masked copy-pastes)."""
    cleaned = value.encode("ascii", errors="ignore").decode("ascii").strip()
    if not cleaned:
        return None
    if cleaned != value.strip():
        logger.warning(
            "Non-ASCII characters removed from QDRANT_API_KEY. "
            "The value in .env appears to have been copy-pasted from a masked UI — "
            "please replace it with the real key."
        )
    return cleaned


@asynccontextmanager
async def lifespan(app: FastAPI):
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:
        logger.warning(f"Database table creation failed (non-fatal): {exc}")

    # ── Qdrant ────────────────────────────────────────────────────────────────
    app.state.qdrant_client = None
    app.state.search_engine = None

    try:
        api_key = _sanitize_ascii(settings.qdrant_api_key)
        qdrant_client = QdrantClient(
            url=settings.qdrant_url,
            api_key=api_key,
        )
        collections = [c.name for c in qdrant_client.get_collections().collections]
        if settings.qdrant_collection not in collections:
            qdrant_client.create_collection(
                collection_name=settings.qdrant_collection,
                vectors_config=VectorParams(size=768, distance=Distance.COSINE),
            )
            logger.info(f"Created Qdrant collection: {settings.qdrant_collection}")

        try:
            from qdrant_client.models import PayloadSchemaType
            qdrant_client.create_payload_index(
                collection_name=settings.qdrant_collection,
                field_name="source_type",
                field_schema=PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass

        app.state.qdrant_client = qdrant_client

        from app.retrieval.hybrid_search import HybridSearchEngine
        search_engine = HybridSearchEngine(qdrant_client, settings.qdrant_collection)
        app.state.search_engine = search_engine

        import asyncio
        asyncio.create_task(_refresh_bm25(search_engine))
    except Exception as exc:
        logger.warning(
            f"Qdrant initialization failed — vector search unavailable: {exc}. "
            "Check QDRANT_URL and QDRANT_API_KEY in .env."
        )

    # ── Default admin user ────────────────────────────────────────────────────
    try:
        from app.api.auth import hash_password
        from app.database import AsyncSessionLocal
        from app.models.user import User
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            admin = await db.scalar(select(User).where(User.email == "admin@aivaura.com"))
            if not admin:
                admin = User(
                    email="admin@aivaura.com",
                    hashed_password=hash_password("changeme123"),
                    role="admin",
                )
                db.add(admin)
                await db.commit()
                logger.info("Created default admin user: admin@aivaura.com / changeme123")
    except Exception as exc:
        logger.warning(f"Admin user seed failed (non-fatal): {exc}")

    logger.info("Context Store API started")
    yield

    await engine.dispose()
    logger.info("Context Store API stopped")


async def _refresh_bm25(search_engine):
    try:
        from app.database import AsyncSessionLocal
        from app.models.chunk import Chunk
        from app.models.connector import Connector
        from app.models.document import Document
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            chunks = (
                await db.scalars(
                    select(Chunk)
                    .join(Document)
                    .join(Connector)
                    .where(Chunk.qdrant_id.is_not(None))
                    .limit(50000)
                )
            ).all()

            bm25_docs = [
                {
                    "chunk_id": c.qdrant_id,
                    "document_id": str(c.document_id),
                    "text": c.text,
                    "source_type": "",
                    "source_name": "",
                    "document_title": "",
                    "document_url": "",
                    "author": "",
                    "date": "",
                    "chunk_index": c.chunk_index,
                }
                for c in chunks
            ]

            if bm25_docs:
                search_engine.refresh_bm25(bm25_docs)
                logger.info(f"BM25 index refreshed with {len(bm25_docs)} chunks")
    except Exception as e:
        logger.warning(f"BM25 refresh failed (non-fatal): {e}")


app = FastAPI(
    title="Context Store API",
    description="Aivaura Company Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"data": None, "error": "Internal server error"},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "service": "context-store"}


from app.api import admin, auth, connectors, documents, graph, notes, query, webhooks

app.include_router(auth.router, prefix="/api/v1")
app.include_router(connectors.router, prefix="/api/v1")
app.include_router(query.router, prefix="/api/v1")
app.include_router(documents.router, prefix="/api/v1")
app.include_router(notes.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")

