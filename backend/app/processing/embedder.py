import httpx

from app.config import get_settings


async def embed_text(text: str) -> list[float]:
    if not text or not text.strip():
        text = "empty document chunk"
    settings = get_settings()
    if settings.embed_provider == "jina":
        return await _embed_jina(text, settings)
    return await _embed_ollama(text, settings)


async def embed_batch(texts: list[str]) -> list[list[float]]:
    return [await embed_text(t) for t in texts]


async def _embed_ollama(text: str, settings) -> list[float]:
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.ollama_base_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]


async def _embed_jina(text: str, settings) -> list[float]:
    import asyncio
    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(5):
            try:
                response = await client.post(
                    "https://api.jina.ai/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {settings.jina_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={"model": settings.jina_embed_model, "input": [text]},
                )
                if response.status_code == 429 and attempt < 4:
                    await asyncio.sleep(2.0 * (2 ** attempt))
                    continue
                response.raise_for_status()
                return response.json()["data"][0]["embedding"]
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < 4:
                    await asyncio.sleep(2.0 * (2 ** attempt))
                else:
                    raise
        raise RuntimeError("Failed to obtain embedding from Jina AI after retries")
