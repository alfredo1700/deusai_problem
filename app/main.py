"""FastAPI application exposing the DEUS Bank multi-agent support graph."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import get_settings
from app.graph.graph import support_graph
from app.schemas.api import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ClientType,
    ConversationPhase,
    HealthResponse,
    VoiceChatResponse,
)
from app.services.sessions import session_store
from app.services.stt import SpeechToTextError, transcribe_audio

settings = get_settings()
_STATIC_DIR = Path(__file__).resolve().parent / "static"
_MAX_AUDIO_BYTES = 8 * 1024 * 1024

app = FastAPI(
    title=settings.app_name,
    description="AI-powered multi-agent customer support for DEUS Bank (LangGraph + FastAPI).",
    version="1.0.0",
)


def _history(state: dict) -> list[ChatMessage]:
    messages = state.get("messages") or []
    return [ChatMessage(role=m.get("role", "user"), content=m.get("content", "")) for m in messages]


def _user_turn_count(state: dict) -> int:
    return sum(1 for m in (state.get("messages") or []) if m.get("role") == "user")


def _to_chat_response(session_id: str, result: dict) -> ChatResponse:
    phase = result.get("phase") or ConversationPhase.GREETING
    client_type = result.get("client_type") or ClientType.UNKNOWN
    reply = result.get("reply") or (
        "I'm here to help. Please share two of: name, phone, and IBAN."
    )
    return ChatResponse(
        session_id=session_id,
        reply=reply,
        phase=phase,
        client_type=client_type,
        fully_verified=bool(result.get("fully_verified")),
        turn=_user_turn_count(result),
        history=_history(result),
        metadata=dict(result.get("metadata") or {}),
    )


def run_text_turn(session_id: str, message: str) -> ChatResponse:
    """Single text turn into the compiled graph. Voice and /chat both use this."""
    state = session_store.get(session_id)
    state["latest_user_message"] = message
    state["messages"] = list(state.get("messages") or []) + [
        {"role": "user", "content": message}
    ]
    state["reply"] = ""
    state["blocked"] = False
    state["halt_turn"] = False

    result = support_graph.invoke(state)
    session_store.save(session_id, result)
    return _to_chat_response(session_id, result)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, llm_mode=settings.llm_mode)


@app.get("/voice")
def voice_demo() -> FileResponse:
    page = _STATIC_DIR / "voice.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="Voice demo page is missing")
    return FileResponse(page)


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    return run_text_turn(payload.session_id, payload.message)


@app.post("/chat/voice", response_model=VoiceChatResponse)
async def chat_voice(
    session_id: str = Form(..., min_length=1),
    audio: UploadFile = File(...),
    translate: bool = Form(False),
) -> VoiceChatResponse:
    """Optional STT layer: audio → text (optionally translated to English), then the same graph."""
    data = await audio.read()
    if len(data) > _MAX_AUDIO_BYTES:
        raise HTTPException(status_code=413, detail="Audio file is larger than 8 MB")
    try:
        transcript = transcribe_audio(
            data=data,
            filename=audio.filename or "audio.webm",
            translate=translate,
        )
    except SpeechToTextError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    chat_result = run_text_turn(session_id, transcript)
    stt_model = "whisper-1" if translate else settings.whisper_model
    payload = chat_result.model_dump()
    payload["metadata"] = {
        **chat_result.metadata,
        "input": "voice",
        "stt_model": stt_model,
        "translated": translate,
    }
    return VoiceChatResponse(
        **payload,
        transcript=transcript,
        translated=translate,
        stt_model=stt_model,
    )


@app.get("/sessions/{session_id}", response_model=ChatResponse)
def get_session(session_id: str) -> ChatResponse:
    state = session_store.peek(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="Unknown session_id")
    return _to_chat_response(session_id, state)


@app.delete("/sessions/{session_id}")
def reset_session(session_id: str) -> dict[str, str]:
    session_store.clear(session_id)
    return {"status": "cleared", "session_id": session_id}
