"""Sample bank customers and accounts used for identity verification."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserRecord:
    name: str
    phone: str
    iban: str
    secret: str
    answer: str


@dataclass(frozen=True, slots=True)
class AccountRecord:
    iban: str
    premium: bool  # README sample uses typo "premiun"; we normalize to "premium"


USERS: tuple[UserRecord, ...] = (
    UserRecord(
        name="Lisa",
        phone="+1122334455",
        iban="DE89370400440532013000",
        secret="Which is the name of my dog?",
        answer="Yoda",
    ),
    UserRecord(
        name="Marco",
        phone="+34911222333",
        iban="ES9121000418450200051332",
        secret="What city were you born in?",
        answer="Valencia",
    ),
    UserRecord(
        name="Amina",
        phone="+447700900123",
        iban="GB29NWBK60161331926819",
        secret="What is your favorite color?",
        answer="Teal",
    ),
    # Verifiable identity, but no active account row → Bouncer classifies as non-client.
    UserRecord(
        name="Erik",
        phone="+4989001122",
        iban="DE12500105170648489890",
        secret="What is your childhood nickname?",
        answer="Rik",
    ),
)

ACCOUNTS: tuple[AccountRecord, ...] = (
    AccountRecord(iban="DE89370400440532013000", premium=True),  # Lisa
    AccountRecord(iban="ES9121000418450200051332", premium=False),  # Marco (regular)
    AccountRecord(iban="GB29NWBK60161331926819", premium=True),  # Amina
)

# High-value topics that should go through the Specialist agent.
SPECIALIST_KEYWORDS: tuple[str, ...] = (
    "yacht",
    "private jet",
    "private banking",
    "wealth management",
    "offshore",
    "art collection",
    "luxury insurance",
)


def find_users_matching(*, name: str | None, phone: str | None, iban: str | None) -> list[UserRecord]:
    """Return users that match at least one provided identity field."""
    matches: list[UserRecord] = []
    for user in USERS:
        score = 0
        if name and _norm(user.name) == _norm(name):
            score += 1
        if phone and _norm_phone(user.phone) == _norm_phone(phone):
            score += 1
        if iban and _norm(user.iban) == _norm(iban):
            score += 1
        if score:
            matches.append(user)
    return matches


def score_user(user: UserRecord, *, name: str | None, phone: str | None, iban: str | None) -> int:
    score = 0
    if name and _norm(user.name) == _norm(name):
        score += 1
    if phone and _norm_phone(user.phone) == _norm_phone(phone):
        score += 1
    if iban and _norm(user.iban) == _norm(iban):
        score += 1
    return score


def get_account(iban: str) -> AccountRecord | None:
    target = _norm(iban)
    for account in ACCOUNTS:
        if _norm(account.iban) == target:
            return account
    return None


def _norm(value: str) -> str:
    return value.strip().casefold().replace(" ", "")


def _norm_phone(value: str) -> str:
    return "".join(ch for ch in value.strip() if ch.isdigit() or ch == "+")
