import httpx

from app.llm.base import BaseLLM


class OllamaLLM(BaseLLM):
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2:3b"):
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def complete(self, messages: list[dict]) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
