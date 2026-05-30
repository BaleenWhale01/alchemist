"""Configuration loading: YAML file + environment-variable overrides.

Precedence (high → low): environment variables > config.yaml > built-in defaults.
Secrets (API keys, bot tokens) are intentionally resolvable from env so they need
never be written to disk.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .constants import AGENTS, DEFAULT_CONFIG_PATH, DEFAULT_WORKSPACE


def _expand(path: str) -> Path:
    return Path(os.path.expanduser(path)).resolve()


@dataclass
class ProviderConfig:
    name: str = "openrouter"
    api_key: str = ""
    model: str = "anthropic/claude-sonnet-4.6"
    base_url: str = ""

    def resolved_key(self) -> str:
        if self.api_key:
            return self.api_key
        env_name = {
            "openrouter": "OPENROUTER_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
        }.get(self.name, "")
        return os.environ.get(env_name, "") if env_name else ""


@dataclass
class TelegramConfig:
    enabled: bool = True
    group_id: str = ""
    accounts: dict[str, str] = field(default_factory=dict)

    def token_for(self, agent: str) -> str:
        token = (self.accounts or {}).get(agent, "")
        if token:
            return token
        return os.environ.get(f"TELEGRAM_TOKEN_{agent.upper()}", "")


@dataclass
class Config:
    workspace: Path
    provider: ProviderConfig
    telegram: TelegramConfig
    agents: dict[str, dict[str, Any]]
    schedule: dict[str, Any]
    behavior: dict[str, Any]
    path: Path | None = None

    def model_for(self, agent: str) -> str:
        return (self.agents.get(agent) or {}).get("model") or self.provider.model

    @classmethod
    def load(cls, config_path: str | None = None) -> "Config":
        path = _expand(config_path or os.environ.get("ALCHEMIST_CONFIG", DEFAULT_CONFIG_PATH))
        raw: dict[str, Any] = {}
        if path.exists():
            raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

        prov = raw.get("provider", {}) or {}
        provider = ProviderConfig(
            name=prov.get("name", "openrouter"),
            api_key=prov.get("api_key", ""),
            model=prov.get("model", "anthropic/claude-sonnet-4.6"),
            base_url=prov.get("base_url", ""),
        )

        tg = (raw.get("channels", {}) or {}).get("telegram", {}) or {}
        telegram = TelegramConfig(
            enabled=tg.get("enabled", True),
            group_id=str(tg.get("group_id", "") or ""),
            accounts=tg.get("accounts", {}) or {},
        )

        agents = {a: (raw.get("agents", {}) or {}).get(a, {}) or {} for a in AGENTS}

        workspace = _expand(raw.get("workspace", DEFAULT_WORKSPACE))

        return cls(
            workspace=workspace,
            provider=provider,
            telegram=telegram,
            agents=agents,
            schedule=raw.get("schedule", {}) or {},
            behavior=raw.get("behavior", {}) or {},
            path=path if path.exists() else None,
        )
