"""Voice STT adapter tests (OpenAI API is mocked; the graph still receives text)."""

from io import BytesIO
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.stt import SpeechToTextError, transcribe_audio

client = TestClient(app)


def test_voice_without_key_fails_clearly():
    with patch("app.services.stt.get_settings") as settings:
        settings.return_value.openai_api_key = ""
        settings.return_value.whisper_model = "whisper-1"
        try:
            transcribe_audio(data=b"fake", filename="a.wav")
            assert False, "expected SpeechToTextError"
        except SpeechToTextError as exc:
            assert "OPENAI_API_KEY" in str(exc)


def test_chat_voice_feeds_transcript_into_graph():
    audio = BytesIO(b"fake-bytes")
    audio.name = "clip.webm"
    with patch("app.main.transcribe_audio", return_value="Hello"):
        response = client.post(
            "/chat/voice",
            data={"session_id": "voice-unit", "translate": "false"},
            files={"audio": ("clip.webm", audio, "audio/webm")},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["transcript"] == "Hello"
    assert body["translated"] is False
    assert body["phase"] == "collecting_identity"
    assert "DEUS Bank" in body["reply"] or "name" in body["reply"].casefold()


def test_chat_voice_translate_flag_is_forwarded():
    audio = BytesIO(b"fake-bytes")
    with patch("app.main.transcribe_audio", return_value="My name is Lisa") as mocked:
        response = client.post(
            "/chat/voice",
            data={"session_id": "voice-translate", "translate": "true"},
            files={"audio": ("clip.webm", audio, "audio/webm")},
        )
    assert response.status_code == 200
    mocked.assert_called_once()
    assert mocked.call_args.kwargs["translate"] is True
    assert response.json()["translated"] is True
    assert response.json()["transcript"] == "My name is Lisa"
    assert response.json()["phase"] == "collecting_identity"
