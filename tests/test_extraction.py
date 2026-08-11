"""Extraction helper tests."""

from app.graph.extraction import extract_identity_fields, merge_identity


def test_extract_name_phone_iban():
    message = "My name is Lisa, phone +1122334455, IBAN DE89370400440532013000"
    fields = extract_identity_fields(message)
    assert fields["name"] == "Lisa"
    assert fields["phone"] == "+1122334455"
    assert fields["iban"] == "DE89370400440532013000"


def test_extract_field_labels():
    message = "name: Marco phone: +34911222333 iban: ES9121000418450200051332"
    fields = extract_identity_fields(message)
    assert fields["name"] == "Marco"
    assert "34911222333" in (fields["phone"] or "")
    assert fields["iban"] == "ES9121000418450200051332"


def test_merge_identity_keeps_previous_values():
    current = {"name": "Lisa", "phone": None, "iban": None}
    extracted = {"name": None, "phone": "+1122334455", "iban": None}
    merged = merge_identity(current, extracted)
    assert merged == {"name": "Lisa", "phone": "+1122334455", "iban": None}
