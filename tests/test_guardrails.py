"""Guardrail unit tests."""

from app.services.guardrails import (
    classify_guardrail,
    is_disallowed_request,
    is_off_topic,
    redact_sensitive_for_unverified,
    sanitize_outbound,
)


def test_blocks_loan_approval_requests():
    assert is_disallowed_request("Please approve a loan of one million dollars") is True
    assert classify_guardrail("Please approve a loan of one million dollars") == "policy"


def test_allows_normal_support_requests():
    assert is_disallowed_request("I need help with my account balance") is False
    assert classify_guardrail("I need help with my account balance") == "allow"


def test_flags_off_topic_weather_and_jokes():
    assert is_off_topic("What's the weather in Madrid today?") is True
    assert is_off_topic("Tell me a joke about cats") is True
    assert classify_guardrail("What's the weather in Madrid today?") == "off_topic"


def test_identity_and_secret_answers_are_not_off_topic():
    assert classify_guardrail("Yoda") == "allow"
    assert classify_guardrail("My name is Lisa phone +1122334455") == "allow"
    assert classify_guardrail("Hello") == "allow"


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
