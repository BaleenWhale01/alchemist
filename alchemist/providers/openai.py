"""OpenAI provider. Shares OpenRouter's request shape, different base/host."""

from __future__ import annotations

import httpx

from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    DEFAULT_BASE = "https://api.openai.com/v1"

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
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, *messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{base}/chat/completions", json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]
