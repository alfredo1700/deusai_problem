"""Tests for deterministic 2-of-3 identity verification."""

from app.data.bank_data import USERS
from app.services.verification import check_secret_answer, verify_identity


def test_verify_requires_two_fields():
    result = verify_identity(name="Lisa", phone=None, iban=None)
    assert result.matched is False
    assert "at least 2" in result.reason.lower() or "Need at least 2" in result.reason


def test_verify_two_of_three_success():
    lisa = USERS[0]
    result = verify_identity(name=lisa.name, phone=lisa.phone, iban=None)
    assert result.matched is True
    assert result.match_count == 2
    assert result.user is not None
    assert result.user.name == "Lisa"


def test_verify_wrong_combination_fails():
    result = verify_identity(name="Lisa", phone="+0000000000", iban="DE00000000000000000000")
    assert result.matched is False


def test_secret_answer_case_insensitive():
    lisa = USERS[0]
    assert check_secret_answer(lisa, "yoda") is True
    assert check_secret_answer(lisa, "YODA") is True
    assert check_secret_answer(lisa, "wrong") is False
