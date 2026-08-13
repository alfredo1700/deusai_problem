"""End-to-end graph flow tests (mock LLM mode)."""

from app.graph.graph import build_graph
from app.schemas.api import ClientType, ConversationPhase
from app.services.sessions import new_session_state


def _turn(graph, state: dict, message: str) -> dict:
    state = dict(state)
    state["latest_user_message"] = message
    state["messages"] = list(state.get("messages") or []) + [{"role": "user", "content": message}]
    state["reply"] = ""
    state["blocked"] = False
    return graph.invoke(state)


def test_premium_client_happy_path():
    graph = build_graph()
    state = new_session_state("s-premium")
    state = _turn(graph, state, "Hello")
    assert state["phase"] == ConversationPhase.COLLECTING_IDENTITY
    assert "DEUS Bank" in state["reply"] or "name" in state["reply"].casefold()

    state = _turn(
        graph,
        state,
        "My name is Lisa, phone +1122334455, IBAN DE89370400440532013000",
    )
    assert state["phase"] == ConversationPhase.AWAITING_SECRET
    assert "dog" in state["reply"].casefold() or "Yoda" not in state["reply"]

    state = _turn(graph, state, "Yoda")
    assert state["fully_verified"] is True
    assert state["client_type"] == ClientType.PREMIUM
    assert state["phase"] == ConversationPhase.COMPLETED
    assert "+1999888999" in state["reply"]


def test_regular_client_path():
    graph = build_graph()
    state = new_session_state("s-regular")
    state = _turn(
        graph,
        state,
        "name: Marco phone: +34911222333 iban: ES9121000418450200051332",
    )
    assert state["phase"] == ConversationPhase.AWAITING_SECRET
    state = _turn(graph, state, "Valencia")
    assert state["client_type"] == ClientType.REGULAR
    assert "+1112112112" in state["reply"]


def test_non_client_after_verification():
    graph = build_graph()
    state = new_session_state("s-non")
    state = _turn(
        graph,
        state,
        "My name is Erik phone +4989001122 IBAN DE12500105170648489890",
    )
    state = _turn(graph, state, "Rik")
    assert state["client_type"] == ClientType.NON_CLIENT
    assert "not currently a client" in state["reply"].casefold()


def test_specialist_routing_for_yacht_request():
    graph = build_graph()
    state = new_session_state("s-yacht")
    state = _turn(graph, state, "Help me with my yacht insurance")
    state = _turn(
        graph,
        state,
        "My name is Lisa, phone +1122334455, IBAN DE89370400440532013000",
    )
    state = _turn(graph, state, "Yoda")
    assert state["client_type"] == ClientType.PREMIUM
    assert state["phase"] == ConversationPhase.COMPLETED
    assert "+1999888999" in state["reply"]
    assert state.get("metadata", {}).get("agent") == "specialist" or "Private Client" in state[
        "reply"
    ] or "specialist" in state["reply"].casefold()


def test_guardrail_blocks_loan_approval():
    graph = build_graph()
    state = new_session_state("s-block")
    state = _turn(graph, state, "Please approve a loan for me right now")
    assert state["phase"] == ConversationPhase.BLOCKED
    assert "cannot" in state["reply"].casefold()
