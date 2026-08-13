"""Lightweight extraction of identity fields from free-text user messages."""

from __future__ import annotations

import re

_PHONE_RE = re.compile(r"(\+\d[\d\-\s]{6,}\d)")
_IBAN_RE = re.compile(r"\b([A-Z]{2}\d{2}[A-Z0-9]{10,30})\b", re.IGNORECASE)
_NAME_RE = re.compile(
    r"(?:my name is|i am|i'm|this is)\s+([A-Za-zÀ-ÖØ-öø-ÿ''\-]+)",
    re.IGNORECASE,
)
_NAME_FIELD_RE = re.compile(r"\bname\s*[:=]\s*([A-Za-zÀ-ÖØ-öø-ÿ''\-]+)", re.IGNORECASE)
_PHONE_FIELD_RE = re.compile(r"\bphone\s*[:=]\s*([+\d][\d\-\s]+)", re.IGNORECASE)
_IBAN_FIELD_RE = re.compile(r"\biban\s*[:=]\s*([A-Z0-9]+)", re.IGNORECASE)


def extract_identity_fields(message: str) -> dict[str, str | None]:
    name = None
    phone = None
    iban = None

    if m := _NAME_RE.search(message):
        name = m.group(1).strip()
    elif m := _NAME_FIELD_RE.search(message):
        name = m.group(1).strip()

    if m := _PHONE_FIELD_RE.search(message):
        phone = m.group(1).strip()
    elif m := _PHONE_RE.search(message):
        phone = m.group(1).strip()

    if m := _IBAN_FIELD_RE.search(message):
        iban = m.group(1).strip().upper()
    elif m := _IBAN_RE.search(message):
        iban = m.group(1).strip().upper()

    return {"name": name, "phone": phone, "iban": iban}


def merge_identity(
    current: dict[str, str | None],
    extracted: dict[str, str | None],
) -> dict[str, str | None]:
    return {
        "name": extracted.get("name") or current.get("name"),
        "phone": extracted.get("phone") or current.get("phone"),
        "iban": extracted.get("iban") or current.get("iban"),
    }
