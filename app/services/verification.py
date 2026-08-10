"""Deterministic identity verification (2-of-3) and secret-answer checks."""

from __future__ import annotations

from dataclasses import dataclass

from app.data.bank_data import UserRecord, find_users_matching, score_user


@dataclass(frozen=True, slots=True)
class VerificationResult:
    matched: bool
    match_count: int
    user: UserRecord | None
    reason: str


def verify_identity(
    *,
    name: str | None,
    phone: str | None,
    iban: str | None,
    min_matches: int = 2,
) -> VerificationResult:
    """Require at least `min_matches` of {name, phone, iban} against a single user."""
    provided = sum(1 for value in (name, phone, iban) if value)
    if provided < min_matches:
        return VerificationResult(
            matched=False,
            match_count=0,
            user=None,
            reason=f"Need at least {min_matches} identity fields; received {provided}.",
        )

    candidates = find_users_matching(name=name, phone=phone, iban=iban)
    best: UserRecord | None = None
    best_score = 0
    for user in candidates:
        score = score_user(user, name=name, phone=phone, iban=iban)
        if score > best_score:
            best = user
            best_score = score

    if best is None or best_score < min_matches:
        return VerificationResult(
            matched=False,
            match_count=best_score,
            user=None,
            reason="Identity details did not match a known customer (need 2 of 3).",
        )

    return VerificationResult(
        matched=True,
        match_count=best_score,
        user=best,
        reason="Identity verified with 2-of-3 match.",
    )


def check_secret_answer(user: UserRecord, answer: str | None) -> bool:
    if not answer:
        return False
    return answer.strip().casefold() == user.answer.strip().casefold()
