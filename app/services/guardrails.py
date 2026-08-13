"""Policy / safety guardrails for bank support conversations."""

from __future__ import annotations

import re
from typing import Literal

from app.graph.extraction import extract_identity_fields

# Patterns that must never appear in outbound messages to unverified users.
# IBAN is applied before phone so digit-heavy account numbers are not misclassified.
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"\+\d[\d\-\s]{6,}\d")

GuardrailVerdict = Literal["allow", "policy", "off_topic"]

DISALLOWED_TOPICS = (
    "approve a loan",
    "approve loan",
    "wire transfer all",
    "send all my money",
    "hack",
    "bypass verification",
    "ignore previous instructions",
    "jailbreak",
)

LOAN_APPROVAL_RE = re.compile(
    r"\b(approve|grant|authorize)\b.{0,40}\b(loan|credit|mortgage)\b",
    re.IGNORECASE,
)

BANKING_HINTS = (
    "account",
    "iban",
    "phone",
    "bank",
    "support",
    "insurance",
    "card",
    "balance",
    "premium",
    "client",
    "identity",
    "verify",
    "verification",
    "secret",
    "help",
    "name",
    "yacht",
)

OFF_TOPIC_HINTS = (
    "weather",
    "forecast",
    "football",
    "soccer",
    "recipe",
    "cook",
    "joke",
    "poem",
    "movie",
    "celebrity",
    "horoscope",
    "lottery numbers",
    "write me a song",
    "who won the",
)


def is_disallowed_request(message: str) -> bool:
    return classify_guardrail(message) == "policy"


def is_off_topic(message: str) -> bool:
    return classify_guardrail(message) == "off_topic"


def classify_guardrail(message: str) -> GuardrailVerdict:
    """Hard policy blocks first; off-topic is a soft redirect that keeps session state."""
    text = message.casefold()
    if any(topic in text for topic in DISALLOWED_TOPICS) or LOAN_APPROVAL_RE.search(message):
        return "policy"

    extracted = extract_identity_fields(message)
    if any(extracted.values()):
        return "allow"
    if any(hint in text for hint in BANKING_HINTS):
        return "allow"
    if any(hint in text for hint in OFF_TOPIC_HINTS):
        return "off_topic"
    return "allow"


def guardrail_refusal() -> str:
    return (
        "I cannot help with that request. For security and compliance reasons, "
        "DEUS Bank assistants cannot approve loans, move funds, or bypass identity checks. "
        "Please contact an authorized bank representative for regulated actions."
    )


def off_topic_redirect() -> str:
    return (
        "I'm here to help with DEUS Bank customer support: identity verification and "
        "routing to the right desk. I can't help with unrelated topics. "
        "Please share your banking request, or two of: name, phone, and IBAN."
    )


def redact_sensitive_for_unverified(text: str) -> str:
    """Strip phone numbers and IBANs from messages when the caller is not fully verified."""
    redacted = _IBAN_RE.sub("[redacted-iban]", text)
    redacted = _PHONE_RE.sub("[redacted-phone]", redacted)
    return redacted


def sanitize_outbound(text: str, *, fully_verified: bool) -> str:
    if fully_verified:
        return text
    return redact_sensitive_for_unverified(text)
