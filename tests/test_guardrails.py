"""Guardrail unit tests."""

from app.services.guardrails import (
    is_disallowed_request,
    redact_sensitive_for_unverified,
    sanitize_outbound,
)


def test_blocks_loan_approval_requests():
    assert is_disallowed_request("Please approve a loan of one million dollars") is True


def test_allows_normal_support_requests():
    assert is_disallowed_request("I need help with my account balance") is False


def test_redacts_phone_and_iban_for_unverified():
    text = "Call me at +1122334455 or use IBAN DE89370400440532013000"
    redacted = redact_sensitive_for_unverified(text)
    assert "+1122334455" not in redacted
    assert "DE89370400440532013000" not in redacted
    assert "[redacted-phone]" in redacted
    assert "[redacted-iban]" in redacted


def test_sanitize_keeps_pii_when_verified():
    text = "Contact +1999888999"
    assert sanitize_outbound(text, fully_verified=True) == text
