"""
LLM factory — supports OpenAI, Anthropic (Claude), and Ollama.
Provider and API key are set at runtime via /config endpoint.
"""
import os
from dataclasses import dataclass, field
from typing import Literal

Provider = Literal["openai", "anthropic", "ollama"]

@dataclass
class LLMConfig:
    provider: Provider = "ollama"
    api_key: str = ""
    # per-provider model defaults
    openai_model: str = "gpt-4o"
    anthropic_model: str = "claude-sonnet-4-5"
    ollama_model: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen3:8b"))
    ollama_base_url: str = field(default_factory=lambda: os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

# Global config — mutated by /config endpoint
_config = LLMConfig()


def set_config(
    provider: Provider,
    api_key: str = "",
    openai_model: str | None = None,
    anthropic_model: str | None = None,
    ollama_model: str | None = None,
) -> None:
    _config.provider = provider
    _config.api_key = api_key
    if openai_model:
        _config.openai_model = openai_model
    if anthropic_model:
        _config.anthropic_model = anthropic_model
    if ollama_model:
        _config.ollama_model = ollama_model
    print(f"[LLM] Provider set to: {provider}"
          + (f" (model: {openai_model or anthropic_model or ollama_model})" if any([openai_model, anthropic_model, ollama_model]) else ""))


def get_config() -> dict:
    return {
        "provider": _config.provider,
        "has_api_key": bool(_config.api_key),
        "openai_model": _config.openai_model,
        "anthropic_model": _config.anthropic_model,
        "ollama_model": _config.ollama_model,
    }


def get_llm(temperature: float = 0.2):
    """Return a LangChain chat model for the currently configured provider."""
    provider = _config.provider

    if provider == "openai":
        from langchain_openai import ChatOpenAI
        key = _config.api_key or os.getenv("OPENAI_API_KEY", "")
        if not key:
            raise ValueError("OpenAI API key not set. Configure it in the extension popup.")
        return ChatOpenAI(
            model=_config.openai_model,
            api_key=key,
            temperature=temperature,
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        key = _config.api_key or os.getenv("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError("Anthropic API key not set. Configure it in the extension popup.")
        return ChatAnthropic(
            model=_config.anthropic_model,
            api_key=key,
            temperature=temperature,
        )

    # Default: Ollama (local, no key needed)
    from langchain_ollama import ChatOllama
    return ChatOllama(
        model=_config.ollama_model,
        base_url=_config.ollama_base_url,
        temperature=temperature,
    )
