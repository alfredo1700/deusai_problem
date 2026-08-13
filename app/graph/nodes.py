"""LangGraph node implementations for Greeter, verification, Bouncer, Specialist."""

from __future__ import annotations

from app.data.bank_data import SPECIALIST_KEYWORDS, USERS, get_account
from app.graph.extraction import extract_identity_fields, merge_identity
from app.graph.state import AgentState
from app.schemas.api import ClientType, ConversationPhase
from app.services.guardrails import (
    classify_guardrail,
    guardrail_refusal,
    off_topic_redirect,
    sanitize_outbound,
)
from app.services.llm import craft_reply
from app.services.verification import check_secret_answer, verify_identity

PREMIUM_SUPPORT = "+1999888999"
REGULAR_SUPPORT = "+1112112112"


def guardrails_node(state: AgentState) -> dict:
    message = state.get("latest_user_message", "")
    verdict = classify_guardrail(message)
    if verdict == "policy":
        reply = guardrail_refusal()
        return {
            "blocked": True,
            "halt_turn": True,
            "phase": ConversationPhase.BLOCKED,
            "reply": reply,
            "messages": [{"role": "assistant", "content": reply}],
            "metadata": {"guardrail": "policy_violation"},
        }
    if verdict == "off_topic":
        reply = off_topic_redirect()
        return {
            "blocked": False,
            "halt_turn": True,
            "reply": reply,
            "messages": [{"role": "assistant", "content": reply}],
            "metadata": {"guardrail": "off_topic"},
        }
    return {"blocked": False, "halt_turn": False}


def greeter_node(state: AgentState) -> dict:
    """Warm welcome and kick off identity collection when no fields exist yet."""
    if state.get("blocked"):
        return {}

    extracted = extract_identity_fields(state.get("latest_user_message", ""))
    has_any_field = any(
        (
            state.get("name"),
            state.get("phone"),
            state.get("iban"),
            extracted.get("name"),
            extracted.get("phone"),
            extracted.get("iban"),
        )
    )

    # Pass through to identity collection when the user already provided details.
    if has_any_field:
        return {
            "phase": ConversationPhase.COLLECTING_IDENTITY,
            "name": extracted.get("name") or state.get("name"),
            "phone": extracted.get("phone") or state.get("phone"),
            "iban": extracted.get("iban") or state.get("iban"),
        }

    fallback = (
        "Welcome to DEUS Bank. I'm your virtual greeter. "
        "To help you securely, please share at least two of the following: "
        "your full name, phone number, and IBAN."
    )
    reply = craft_reply(
        system=(
            "You are the friendly greeter for DEUS Bank. Ask for identification "
            "(name, phone, IBAN — at least two). Do not reveal customer data."
        ),
        user=state.get("latest_user_message", "hello"),
        fallback=fallback,
    )
    reply = sanitize_outbound(reply, fully_verified=False)
    return {
        "phase": ConversationPhase.COLLECTING_IDENTITY,
        "reply": reply,
        "client_type": ClientType.UNKNOWN,
        "fully_verified": False,
        "messages": [{"role": "assistant", "content": reply}],
        "metadata": {"agent": "greeter"},
    }


def collect_identity_node(state: AgentState) -> dict:
    """Accumulate identity fields and enforce the 2-of-3 match before the secret question."""
    if state.get("blocked") or state.get("fully_verified"):
        return {}

    extracted = extract_identity_fields(state.get("latest_user_message", ""))
    merged = merge_identity(
        {
            "name": state.get("name"),
            "phone": state.get("phone"),
            "iban": state.get("iban"),
        },
        extracted,
    )

    result = verify_identity(
        name=merged.get("name"),
        phone=merged.get("phone"),
        iban=merged.get("iban"),
    )

    updates: dict = {
        "name": merged.get("name"),
        "phone": merged.get("phone"),
        "iban": merged.get("iban"),
        "match_count": result.match_count,
        "phase": ConversationPhase.COLLECTING_IDENTITY,
        "metadata": {"agent": "greeter_verification"},
    }

    if not result.matched or result.user is None:
        provided = [k for k, v in merged.items() if v]
        fallback = (
            "I still need to verify your identity using at least two of: name, phone, and IBAN. "
            f"So far I have: {', '.join(provided) if provided else 'no usable fields'}. "
            "Please provide additional details."
        )
        reply = craft_reply(
            system="Ask politely for more identity fields. Never invent matches or leak PII.",
            user=state.get("latest_user_message", ""),
            fallback=fallback,
        )
        reply = sanitize_outbound(reply, fully_verified=False)
        updates["reply"] = reply
        updates["messages"] = [{"role": "assistant", "content": reply}]
        return updates

    user = result.user
    question = user.secret
    # Keep the secret-question prompt deterministic: LLMs often refuse to "play along"
    # with verification/security questions even when this is an intentional bank flow.
    reply = (
        f"Thank you. I matched your details. For final verification, please answer: {question}"
    )
    reply = sanitize_outbound(reply, fully_verified=False)
    updates.update(
        {
            "phase": ConversationPhase.AWAITING_SECRET,
            "matched_user_name": user.name,
            "matched_iban": user.iban,
            "secret_question": question,
            "reply": reply,
            "messages": [{"role": "assistant", "content": reply}],
            "metadata": {
                "agent": "greeter_verification",
                "verification": result.reason,
                "match_count": result.match_count,
            },
        }
    )
    return updates


def secret_node(state: AgentState) -> dict:
    if state.get("blocked") or state.get("fully_verified"):
        return {}

    user = next((u for u in USERS if u.name == state.get("matched_user_name")), None)
    if user is None:
        reply = (
            "I could not continue verification. Please restart and provide your identity details again."
        )
        return {
            "phase": ConversationPhase.COLLECTING_IDENTITY,
            "matched_user_name": None,
            "matched_iban": None,
            "secret_question": None,
            "reply": reply,
            "messages": [{"role": "assistant", "content": reply}],
        }

    answer = state.get("latest_user_message", "").strip()
    if check_secret_answer(user, answer):
        return {
            "fully_verified": True,
            "secret_answer": answer,
            "phase": ConversationPhase.ROUTING,
            "reply": "",  # Bouncer/Specialist will set the customer-facing reply.
            "metadata": {"agent": "greeter_secret", "secret": "accepted"},
        }

    reply = f"That answer does not match our records. Please try again: {user.secret}"
    reply = sanitize_outbound(reply, fully_verified=False)
    return {
        "phase": ConversationPhase.AWAITING_SECRET,
        "reply": reply,
        "messages": [{"role": "assistant", "content": reply}],
        "metadata": {"agent": "greeter_secret", "secret": "rejected"},
    }


def bouncer_node(state: AgentState) -> dict:
    """Classify regular / premium / non-client after full verification."""
    if state.get("blocked") or not state.get("fully_verified"):
        return {}

    iban = state.get("matched_iban") or state.get("iban")
    account = get_account(iban) if iban else None
    message = state.get("latest_user_message", "")
    prior_request = " ".join(
        m["content"] for m in state.get("messages", []) if m.get("role") == "user"
    )
    needs_specialist = _wants_specialist(message) or _wants_specialist(prior_request)

    if account is None:
        reply = (
            "Thank you for reaching out. It seems that you are not currently a client of DEUS Bank. "
            "I recommend that you contact your bank's support department directly for assistance."
        )
        return {
            "client_type": ClientType.NON_CLIENT,
            "phase": ConversationPhase.COMPLETED,
            "needs_specialist": False,
            "reply": reply,
            "messages": [{"role": "assistant", "content": reply}],
            "metadata": {"agent": "bouncer"},
        }

    if account.premium:
        if needs_specialist:
            return {
                "client_type": ClientType.PREMIUM,
                "phase": ConversationPhase.SPECIALIST,
                "needs_specialist": True,
                "metadata": {"agent": "bouncer", "next": "specialist"},
            }
        reply = (
            "Thank you for reaching out regarding your account issue. As a premium client, "
            "we value your experience and are here to assist you. For immediate support, "
            f"please contact our dedicated support department at {PREMIUM_SUPPORT}."
        )
        return {
            "client_type": ClientType.PREMIUM,
            "phase": ConversationPhase.COMPLETED,
            "needs_specialist": False,
            "reply": reply,
            "messages": [{"role": "assistant", "content": reply}],
            "metadata": {"agent": "bouncer"},
        }

    reply = (
        "I'm sorry to hear that you're having trouble with your account. Since you're a regular client, "
        f"I recommend that you call our support department at {REGULAR_SUPPORT} for assistance."
    )
    return {
        "client_type": ClientType.REGULAR,
        "phase": ConversationPhase.COMPLETED,
        "needs_specialist": False,
        "reply": reply,
        "messages": [{"role": "assistant", "content": reply}],
        "metadata": {"agent": "bouncer"},
    }


def specialist_node(state: AgentState) -> dict:
    if state.get("blocked"):
        return {}
    if state.get("phase") != ConversationPhase.SPECIALIST and not state.get("needs_specialist"):
        return {}

    topic = state.get("latest_user_message", "your high-value request")
    fallback = (
        "Thank you for reaching out regarding your account issue. As a premium client, "
        "we value your experience and are here to assist you. For your high-value request, "
        f"please contact our dedicated specialist desk at {PREMIUM_SUPPORT} "
        "and ask for Private Client Services."
    )
    reply = craft_reply(
        system=(
            "You are the Specialist agent for DEUS Bank premium clients. "
            "Acknowledge the high-value request and route them to Private Client Services "
            f"at {PREMIUM_SUPPORT}. Do not approve products or disclose other customers' data."
        ),
        user=topic,
        fallback=fallback,
    )
    reply = sanitize_outbound(reply, fully_verified=True)
    return {
        "client_type": ClientType.PREMIUM,
        "phase": ConversationPhase.COMPLETED,
        "reply": reply,
        "messages": [{"role": "assistant", "content": reply}],
        "metadata": {"agent": "specialist", "routed_to": "private_client_services"},
    }


def _wants_specialist(message: str) -> bool:
    text = message.casefold()
    return any(keyword in text for keyword in SPECIALIST_KEYWORDS)
