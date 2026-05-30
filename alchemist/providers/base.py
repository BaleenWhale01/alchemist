"""Provider abstraction.

Every agent talks to the LLM through this one async method. Keeping the surface
tiny (chat completion + optional JSON mode) is what makes providers swappable.
"""

from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

from ..config import ProviderConfig


class LLMProvider(ABC):
    def __init__(self, cfg: ProviderConfig):
        self.cfg = cfg
        key = cfg.resolved_key()
        if not key:
            raise RuntimeError(
                f"No API key for provider {cfg.name!r}. Set it in config.provider.api_key "
                f"or the matching env var."
            )
        self.api_key = key

    @abstractmethod
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
        """Return the assistant's text reply."""

    async def complete_json(self, **kwargs: Any) -> dict[str, Any]:
        """complete() but parse the reply as JSON, tolerating code fences/prose."""
        kwargs["json_mode"] = True
        text = await self.complete(**kwargs)
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        text = text.strip()
        # strip ```json ... ``` fences if present
        fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # last resort: grab the outermost {...}
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start : end + 1])
            raise
