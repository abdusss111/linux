import os
from typing import Optional
from openai import OpenAI

class WhisperService:
    """Wrapper around OpenAI Audio Transcriptions/Translations.

    Uses environment variable OPENAI_API_KEY.
    """
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=api_key)

    def transcribe_file(self, file_bytes: bytes, filename: str, *, model: str = "gpt-4o-mini-transcribe", response_format: str = "json", prompt: Optional[str] = None, translate: bool = False) -> dict:
        """Send file to OpenAI transcription/translation.

        Some upload parts (e.g. .part0) lack proper extension; OpenAI infers format
        partly from filename. We normalize to .mp3 if unsupported suffix.
        """
        import io
        supported_ext = {".flac",".m4a",".mp3",".mp4",".mpeg",".mpga",".oga",".ogg",".wav",".webm"}
        original = filename or "audio"
        parts = original.split('.')
        chosen = None
        # Scan left->right to find earliest supported extension; keeps everything before it, drops trailing tokens
        for i in range(1, len(parts)+1):
            candidate = '.' + parts[i-1].lower()
            if candidate in supported_ext:
                chosen = '.'.join(parts[:i])  # keep up to extension
                break
        if not chosen:
            # No supported ext found – fallback
            chosen = (parts[0] or 'audio') + '.mp3'
        base = chosen
        f = io.BytesIO(file_bytes)
        f.name = base
        if translate:
            result = self.client.audio.translations.create(
                model="whisper-1",  # translations only supported on whisper-1 per docs
                file=f,
                response_format=response_format,
                **({"prompt": prompt} if prompt else {})
            )
        else:
            result = self.client.audio.transcriptions.create(
                model=model,
                file=f,
                response_format=response_format,
                **({"prompt": prompt} if prompt else {})
            )
        # result is a pydantic-like object; convert to dict
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        if isinstance(result, dict):
            return result
        return dict(result)
