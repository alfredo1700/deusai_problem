"""OpenAI Speech-to-Text adapter. The LangGraph agents never see audio."""

from __future__ import annotations

from io import BytesIO

from app.config import Settings, get_settings

# Audio translations (into English) only support whisper-1.
_TRANSLATION_MODEL = "whisper-1"


class SpeechToTextError(RuntimeError):
    pass


def transcribe_audio(
    *,
    data: bytes,
    filename: str,
    translate: bool = False,
    settings: Settings | None = None,
) -> str:
    """Turn an audio clip into text via the OpenAI API. No local Whisper weights."""
    cfg = settings or get_settings()
    if not cfg.openai_api_key:
        raise SpeechToTextError(
            "OPENAI_API_KEY is required for voice input. Text /chat still works without it."
        )
    if not data:
        raise SpeechToTextError("Empty audio payload.")

    from openai import OpenAI

    client = OpenAI(api_key=cfg.openai_api_key)
    buffer = BytesIO(data)
    buffer.name = filename or "audio.webm"

    try:
        if translate:
            result = client.audio.translations.create(model=_TRANSLATION_MODEL, file=buffer)
        else:
            result = client.audio.transcriptions.create(model=cfg.whisper_model, file=buffer)
    except Exception as exc:  # noqa: BLE001 — surface API errors as a single STT failure
        raise SpeechToTextError(f"OpenAI transcription failed: {exc}") from exc

    text = (getattr(result, "text", None) or "").strip()
    if not text:
        raise SpeechToTextError("The transcription was empty. Try speaking more clearly.")
    return text
