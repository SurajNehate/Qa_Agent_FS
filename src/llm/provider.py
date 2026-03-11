"""Multi-LLM provider factory.

Supports OpenAI, Groq, and Ollama behind a common BaseChatModel interface.
Selected via LLM_PROVIDER + LLM_MODEL environment variables or explicit config.
"""

import os
from typing import Literal

from pydantic import BaseModel, Field
from langchain_core.language_models.chat_models import BaseChatModel


class LLMConfig(BaseModel):
    """Configuration for LLM provider and model."""

    provider: Literal["openai", "groq", "ollama"] = Field(
        default_factory=lambda: os.getenv("LLM_PROVIDER", "groq")
    )
    model: str = Field(
        default_factory=lambda: os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
    )
    temperature: float = Field(
        default_factory=lambda: float(os.getenv("LLM_TEMPERATURE", "0.2"))
    )


# Default model suggestions per provider (for UI dropdowns)
PROVIDER_MODELS: dict[str, list[str]] = {
    "openai": ["gpt-4.1-nano", "gpt-5-nano", "gpt-5.4"],
    "groq": ["openai/gpt-oss-120b", "llama-3.1-8b-instant"],
    "ollama": ["llama3.1:8b", "mistral:7b", "phi3.5:3.8b"],
}


def get_llm(config: LLMConfig | None = None) -> BaseChatModel:
    """Create and return an LLM instance based on the provider config.

    Args:
        config: LLM configuration. If None, reads from env vars.

    Returns:
        A LangChain BaseChatModel instance.

    Raises:
        ValueError: If the provider is not supported.
    """
    if config is None:
        config = LLMConfig()

    if config.provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            api_key=os.getenv("OPENAI_API_KEY"),
        )

    elif config.provider == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=config.model,
            temperature=config.temperature,
            api_key=os.getenv("GROQ_API_KEY"),
        )

    elif config.provider == "ollama":
        from langchain_ollama import ChatOllama

        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        return ChatOllama(
            model=config.model,
            temperature=config.temperature,
            base_url=base_url,
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: '{config.provider}'. "
            f"Choose from: openai, groq, ollama"
        )
