from functools import lru_cache

from app.config import get_settings
from app.llm.base import BaseLLM


@lru_cache
def get_llm() -> BaseLLM:
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "groq":
        from app.llm.groq import GroqLLM
        return GroqLLM(api_key=settings.groq_api_key, model=settings.groq_model)

    if provider == "anthropic":
        from app.llm.anthropic import AnthropicLLM
        return AnthropicLLM(api_key=settings.anthropic_api_key)

    if provider == "openai":
        from app.llm.openai import OpenAILLM
        return OpenAILLM(api_key=settings.openai_api_key)

    if provider == "ollama":
        from app.llm.ollama import OllamaLLM
        return OllamaLLM(base_url=settings.ollama_base_url, model=settings.ollama_model)

    raise ValueError(f"Unknown LLM provider: {provider}. Choose from: groq, anthropic, openai, ollama")
