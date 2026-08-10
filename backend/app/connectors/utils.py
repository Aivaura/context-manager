import json

import httpx
from cryptography.fernet import Fernet

from app.config import get_settings


def get_fernet() -> Fernet:
    settings = get_settings()
    return Fernet(settings.encryption_key.encode())


def encrypt_token(token_dict: dict) -> str:
    f = get_fernet()
    return f.encrypt(json.dumps(token_dict).encode()).decode()


def decrypt_token(encrypted: str) -> dict:
    f = get_fernet()
    return json.loads(f.decrypt(encrypted.encode()))


async def refresh_microsoft_token(token_dict: dict) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://login.microsoftonline.com/{settings.microsoft_tenant_id}/oauth2/v2.0/token",
            data={
                "client_id": settings.microsoft_client_id,
                "client_secret": settings.microsoft_client_secret,
                "grant_type": "refresh_token",
                "refresh_token": token_dict.get("refresh_token"),
                "scope": "https://graph.microsoft.com/Mail.Read offline_access",
            },
        )
        if response.status_code == 200:
            new_tokens = response.json()
            token_dict.update(new_tokens)
    return token_dict
