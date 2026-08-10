import anthropic

from app.llm.base import BaseLLM


class AnthropicLLM(BaseLLM):
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(self, messages: list[dict]) -> str:
        system_content = ""
        filtered_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_content = msg["content"]
            else:
                filtered_messages.append(msg)

        kwargs: dict = {
            "model": self.model,
            "max_tokens": 2048,
            "messages": filtered_messages,
        }
        if system_content:
            kwargs["system"] = system_content

        response = await self.client.messages.create(**kwargs)
        return response.content[0].text
