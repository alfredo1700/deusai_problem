"""LangGraph conversation state for the multi-agent bank support flow."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from app.schemas.api import ClientType, ConversationPhase


def _merge_dict(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class AgentState(TypedDict, total=False):
    session_id: str
    messages: Annotated[list[dict[str, str]], operator.add]
    latest_user_message: str
    reply: str
    phase: ConversationPhase
    client_type: ClientType
    fully_verified: bool

    # Collected identity fields
    name: str | None
    phone: str | None
    iban: str | None
    secret_answer: str | None

    matched_user_name: str | None
    matched_iban: str | None
    secret_question: str | None
    match_count: int

    needs_specialist: bool
    blocked: bool
    halt_turn: bool
    metadata: Annotated[dict[str, Any], _merge_dict]
