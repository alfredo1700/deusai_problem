"""LLM helpers: OpenAI via LangChain, or deterministic mock mode."""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.config import Settings, get_settings

_REFUSAL_MARKERS = (
    "i can't assist",
    "i cannot assist",
    "i'm sorry, but i can't",
    "i am unable to",
    "i won't be able to help",
    "as an ai",
    "cannot help with that",
)


def get_chat_model(settings: Settings | None = None) -> BaseChatModel | None:
    """Return a chat model when LLM_MODE=openai; otherwise None (mock path)."""
    cfg = settings or get_settings()
    if cfg.llm_mode.casefold() != "openai":
        return None
    if not cfg.openai_api_key:
        return None
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(api_key=cfg.openai_api_key, model=cfg.openai_model, temperature=0.2)


def looks_like_refusal(text: str) -> bool:
    lowered = text.casefold()
    return any(marker in lowered for marker in _REFUSAL_MARKERS)


def craft_reply(
    *,
    system: str,
    user: str,
    fallback: str,
    settings: Settings | None = None,
) -> str:
    """Prefer LLM phrasing, but never ship model refusals for bank flow messages."""
    model = get_chat_model(settings)
    if model is None:
        return fallback
    try:
        response = model.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        content = response.content
        if isinstance(content, str) and content.strip() and not looks_like_refusal(content):
            return content.strip()
    except Exception:
        return fallback
    return fallback
