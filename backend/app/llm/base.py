from abc import ABC, abstractmethod


class BaseLLM(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict]) -> str:
        raise NotImplementedError

    async def complete_with_system(self, system: str, user: str) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return await self.complete(messages)
