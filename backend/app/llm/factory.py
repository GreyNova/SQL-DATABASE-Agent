"""LLM factory — picks the configured provider so the rest of the app is agnostic.

To add a provider: extend `_build()` and add the env vars to `Settings`.
"""
from __future__ import annotations

from functools import lru_cache

from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings


@lru_cache
def get_llm(temperature: float | None = None, streaming: bool = False) -> BaseChatModel:
    """Return a cached chat model for the configured provider."""
    return _build(temperature=temperature, streaming=streaming)


def _build(temperature: float | None, streaming: bool) -> BaseChatModel:
    if getattr(settings, "mock_llm", False):
        from app.llm.mock import MockChatModel
        return MockChatModel()

    provider = settings.llm_provider

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")
        kwargs = {}
        if settings.openai_api_base:
            kwargs["openai_api_base"] = settings.openai_api_base
        return ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=settings.openai_temperature if temperature is None else temperature,
            timeout=settings.openai_request_timeout,
            streaming=streaming,
            **kwargs
        )

    if provider == "azure_openai":
        from langchain_openai import AzureChatOpenAI

        return AzureChatOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_deployment=settings.azure_openai_deployment,
            api_version=settings.azure_openai_api_version,
            api_key=settings.azure_openai_api_key,
            temperature=settings.openai_temperature if temperature is None else temperature,
            streaming=streaming,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key,
            temperature=settings.openai_temperature if temperature is None else temperature,
            streaming=streaming,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is not set.")
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.gemini_api_key,
            temperature=settings.openai_temperature if temperature is None else temperature,
            max_retries=6,  # Retry on 429 rate limit errors (Gemini Free Tier limit: 15 RPM)
            streaming=streaming,
        )

    raise ValueError(f"Unknown LLM provider: {provider!r}")
