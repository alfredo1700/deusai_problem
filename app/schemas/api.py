"""API and domain schemas."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ClientType(str, Enum):
    UNKNOWN = "unknown"
    NON_CLIENT = "non_client"
    REGULAR = "regular"
    PREMIUM = "premium"


class ConversationPhase(str, Enum):
    GREETING = "greeting"
    COLLECTING_IDENTITY = "collecting_identity"
    AWAITING_SECRET = "awaiting_secret"
    ROUTING = "routing"
    SPECIALIST = "specialist"
    COMPLETED = "completed"
    BLOCKED = "blocked"


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, description="Client session identifier")
    message: str = Field(..., min_length=1, description="User utterance")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    phase: ConversationPhase
    client_type: ClientType
    fully_verified: bool
    turn: int = 0
    history: list[ChatMessage] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str
    app: str
    llm_mode: str
