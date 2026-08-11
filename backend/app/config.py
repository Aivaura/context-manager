from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8-sig", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/contextstore"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "company_knowledge"

    # Security
    secret_key: str = "changeme-generate-with-openssl-rand-hex-32"
    encryption_key: str = ""
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # LLM
    llm_provider: str = "groq"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-70b-versatile"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_embed_model: str = "nomic-embed-text"
    embed_provider: str = "ollama"  # "ollama" or "jina"
    jina_api_key: str = ""
    jina_embed_model: str = "jina-embeddings-v2-base-en"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # Microsoft OAuth
    microsoft_client_id: str = ""
    microsoft_client_secret: str = ""
    microsoft_tenant_id: str = "common"

    # WhatsApp
    whatsapp_verify_token: str = "context-store-verify"
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    # CORS
    frontend_url: str = "http://localhost:3000"
    backend_url: str = "http://localhost:8000"

    @property
    def google_redirect_uri_drive(self) -> str:
        return f"{self.backend_url}/api/v1/connectors/google_drive/callback"

    @property
    def google_redirect_uri_gmail(self) -> str:
        return f"{self.backend_url}/api/v1/connectors/gmail/callback"

    @property
    def google_redirect_uri_sheets(self) -> str:
        return f"{self.backend_url}/api/v1/connectors/sheets/callback"

    @property
    def microsoft_redirect_uri(self) -> str:
        return f"{self.backend_url}/api/v1/connectors/outlook/callback"


@lru_cache
def get_settings() -> Settings:
    return Settings()
