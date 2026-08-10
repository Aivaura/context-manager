from groq import AsyncGroq

from app.llm.base import BaseLLM


class GroqLLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "llama-3.1-70b-versatile"):
        self.client = AsyncGroq(api_key=api_key)
        self.model = model

    async def complete(self, messages: list[dict]) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=2048,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""
