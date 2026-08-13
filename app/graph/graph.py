"""Compile the multi-agent LangGraph for DEUS Bank support."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    bouncer_node,
    collect_identity_node,
    followup_node,
    greeter_node,
    guardrails_node,
    secret_node,
    specialist_node,
    _wants_specialist,
)
from app.graph.state import AgentState
from app.schemas.api import ClientType, ConversationPhase


def _after_guardrails(state: AgentState) -> str:
    if state.get("blocked") or state.get("halt_turn"):
        return "end"
    if state.get("fully_verified"):
        phase = state.get("phase")
        latest = state.get("latest_user_message", "")
        if phase == ConversationPhase.COMPLETED:
            if state.get("client_type") == ClientType.PREMIUM and _wants_specialist(latest):
                return "specialist"
            return "followup"
        return "bouncer"
    phase = state.get("phase")
    if phase == ConversationPhase.AWAITING_SECRET:
        return "secret"
    if phase in (None, ConversationPhase.GREETING) and not any(
        (state.get("name"), state.get("phone"), state.get("iban"))
    ):
        # First contact with no prior identity in state — still inspect message in greeter.
        return "greeter"
    if phase in (None, ConversationPhase.GREETING, ConversationPhase.COLLECTING_IDENTITY):
        return "collect_identity"
    if phase == ConversationPhase.SPECIALIST:
        return "specialist"
    if phase == ConversationPhase.COMPLETED:
        return "bouncer"
    return "greeter"


def _after_greeter(state: AgentState) -> str:
    # If the greeter only forwarded extracted fields, continue into verification.
    has_fields = any((state.get("name"), state.get("phone"), state.get("iban")))
    if has_fields and not state.get("reply"):
        return "collect_identity"
    # Greeter already asked the caller for identification.
    if state.get("reply"):
        return "end"
    return "collect_identity"


def _after_secret(state: AgentState) -> str:
    if state.get("fully_verified"):
        return "bouncer"
    return "end"


def _after_bouncer(state: AgentState) -> str:
    if state.get("phase") == ConversationPhase.SPECIALIST or state.get("needs_specialist"):
        return "specialist"
    return "end"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("guardrails", guardrails_node)
    graph.add_node("greeter", greeter_node)
    graph.add_node("collect_identity", collect_identity_node)
    graph.add_node("secret", secret_node)
    graph.add_node("bouncer", bouncer_node)
    graph.add_node("specialist", specialist_node)
    graph.add_node("followup", followup_node)

    graph.add_edge(START, "guardrails")
    graph.add_conditional_edges(
        "guardrails",
        _after_guardrails,
        {
            "end": END,
            "greeter": "greeter",
            "collect_identity": "collect_identity",
            "secret": "secret",
            "bouncer": "bouncer",
            "specialist": "specialist",
            "followup": "followup",
        },
    )
    graph.add_conditional_edges(
        "greeter",
        _after_greeter,
        {"end": END, "collect_identity": "collect_identity"},
    )
    graph.add_edge("collect_identity", END)
    graph.add_conditional_edges(
        "secret",
        _after_secret,
        {"end": END, "bouncer": "bouncer"},
    )
    graph.add_conditional_edges(
        "bouncer",
        _after_bouncer,
        {"end": END, "specialist": "specialist"},
    )
    graph.add_edge("specialist", END)
    graph.add_edge("followup", END)
    return graph.compile()


# Module-level compiled graph for reuse across requests.
support_graph = build_graph()
