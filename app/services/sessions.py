"""In-memory session store with conversation history."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any

from app.schemas.api import ClientType, ConversationPhase


def new_session_state(session_id: str) -> dict[str, Any]:
    return {
        "session_id": session_id,
        "messages": [],
        "latest_user_message": "",
        "reply": "",
        "phase": ConversationPhase.GREETING,
        "client_type": ClientType.UNKNOWN,
        "fully_verified": False,
        "name": None,
        "phone": None,
        "iban": None,
        "secret_answer": None,
        "matched_user_name": None,
        "matched_iban": None,
        "secret_question": None,
        "match_count": 0,
        "needs_specialist": False,
        "blocked": False,
        "metadata": {},
    }


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = new_session_state(session_id)
            return deepcopy(self._sessions[session_id])

    def save(self, session_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            self._sessions[session_id] = deepcopy(state)

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)


session_store = SessionStore()
