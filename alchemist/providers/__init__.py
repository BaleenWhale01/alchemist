"""LLM provider adapters. Swappable via config.provider.name."""

from __future__ import annotations

from ..config import ProviderConfig
from .base import LLMProvider


def build_provider(cfg: ProviderConfig) -> LLMProvider:
    name = cfg.name.lower()
    if name == "openrouter":
        from .openrouter import OpenRouterProvider

        return OpenRouterProvider(cfg)
    if name == "anthropic":
        from .anthropic import AnthropicProvider

        return AnthropicProvider(cfg)
    if name == "openai":
        from .openai import OpenAIProvider

        return OpenAIProvider(cfg)
    raise ValueError(f"Unknown provider: {cfg.name!r} (expected openrouter|anthropic|openai)")


__all__ = ["LLMProvider", "build_provider"]
