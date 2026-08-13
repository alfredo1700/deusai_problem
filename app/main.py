"""FastAPI application exposing the DEUS Bank multi-agent support graph."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.config import get_settings
from app.graph.graph import support_graph
from app.schemas.api import (
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ClientType,
    ConversationPhase,
    HealthResponse,
)
from app.services.sessions import session_store

settings = get_settings()

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


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", app=settings.app_name, llm_mode=settings.llm_mode)


@app.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    state = session_store.get(payload.session_id)
    state["latest_user_message"] = payload.message
    state["messages"] = list(state.get("messages") or []) + [
        {"role": "user", "content": payload.message}
    ]
    # Reset per-turn reply; nodes append assistant messages when they respond.
    state["reply"] = ""
    state["blocked"] = False
    state["halt_turn"] = False

    result = support_graph.invoke(state)
    session_store.save(payload.session_id, result)
    return _to_chat_response(payload.session_id, result)


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
