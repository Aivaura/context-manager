import os
import tempfile

import httpx


async def transcribe_audio(audio_url: str, access_token: str) -> str:
    try:
        import whisper
    except ImportError:
        return "[Voice note transcription unavailable — install openai-whisper]"

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(audio_url, headers={"Authorization": f"Bearer {access_token}"})
        response.raise_for_status()
        audio_bytes = response.content

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        model = whisper.load_model("base")
        result = model.transcribe(tmp_path)
        return result["text"].strip()
    finally:
        os.unlink(tmp_path)
