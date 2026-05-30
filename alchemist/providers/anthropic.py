"""Anthropic provider. Native Messages API (system is a top-level field)."""

from __future__ import annotations

import httpx

from .base import LLMProvider


class AnthropicProvider(LLMProvider):
    DEFAULT_BASE = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict[str, str]],
        model: str,
        json_mode: bool = False,
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> str:
        base = self.cfg.base_url or self.DEFAULT_BASE
        sys = system
        if json_mode:
            sys = system + "\n\nRespond with a single valid JSON object and nothing else."
        payload = {
            "model": model,
            "system": sys,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{base}/messages", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        # concatenate text blocks
        return "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
