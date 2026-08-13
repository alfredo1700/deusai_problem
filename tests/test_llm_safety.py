"""Safety checks around optional LLM phrasing."""

from app.services.llm import looks_like_refusal


def test_looks_like_refusal_detects_common_phrases():
    assert looks_like_refusal("I'm sorry, but I can't assist with that.") is True
    assert looks_like_refusal("Thank you. Please answer: Which is the name of my dog?") is False
