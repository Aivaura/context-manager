from functools import lru_cache

import httpx

from app.config import get_settings


async def embed_text(text: str) -> list[float]:
    settings = get_settings()
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
        )
        response.raise_for_status()
        data = response.json()
        return data["embedding"]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    results = []
    for text in texts:
        embedding = await embed_text(text)
        results.append(embedding)
    return results
