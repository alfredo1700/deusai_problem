"""Policy / safety guardrails for bank support conversations."""

from __future__ import annotations

import re

# Patterns that must never appear in outbound messages to unverified users.
# IBAN is applied before phone so digit-heavy account numbers are not misclassified.
_IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"\+\d[\d\-\s]{6,}\d")

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


def is_disallowed_request(message: str) -> bool:
    text = message.casefold()
    if any(topic in text for topic in DISALLOWED_TOPICS):
        return True
    return bool(LOAN_APPROVAL_RE.search(message))


def guardrail_refusal() -> str:
    return (
        "I cannot help with that request. For security and compliance reasons, "
        "DEUS Bank assistants cannot approve loans, move funds, or bypass identity checks. "
        "Please contact an authorized bank representative for regulated actions."
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
