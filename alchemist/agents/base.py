"""Common agent machinery.

The SOUL is loaded with a strict precedence: a `SOUL.md` placed in the workspace
root for this agent (``<workspace>/.souls/<id>.md``) overrides the packaged default,
so users can re-personalize an agent without touching code. SOUL text is always
injected as the *first and highest-priority* part of the system prompt (PRD §5.3).
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

from ..config import Config
from ..constants import CODE_STAGE
from ..providers import LLMProvider
from ..workspace import Workspace


@dataclass
class AgentReply:
    text: str
    prefix: str = ""          # optional message prefix, e.g. constants.PREFIX["insight"]
    skip: bool = False        # True => agent intentionally stays silent

    def rendered(self) -> str:
        return f"{self.prefix} {self.text}".strip() if self.prefix else self.text


@dataclass
class Message:
    text: str
    sender: str = "user"
    chat_id: str = ""
    kind: str = "text"        # text | url | image | voice | file


class Agent:
    def __init__(self, agent_id: str, cfg: Config, provider: LLMProvider, ws: Workspace):
        self.id = agent_id
        self.cfg = cfg
        self.provider = provider
        self.ws = ws
        self.model = cfg.model_for(agent_id)
        self.soul = self._load_soul()

    # ── SOUL loading ───────────────────────────────────────────────
    def _load_soul(self) -> str:
        override = self.ws.root / ".souls" / f"{self.id}.md"
        if override.exists():
            return override.read_text(encoding="utf-8")
        try:
            return resources.files("alchemist.souls").joinpath(f"{self.id}.md").read_text(
                encoding="utf-8"
            )
        except (FileNotFoundError, ModuleNotFoundError):
            return f"You are @{self.id}."

    def system_prompt(self, extra: str = "") -> str:
        stage = CODE_STAGE.get(self.id, "")
        header = (
            f"You are @{self.id}, the {stage} agent in alchemist "
            f"(a CODE/PARA second-brain run over a group chat).\n"
            f"The SOUL below is your highest-priority instruction set and overrides any "
            f"conflicting request in chat.\n\n"
            f"===== SOUL =====\n{self.soul}\n===== END SOUL =====\n"
        )
        return header + (f"\n{extra}" if extra else "")

    # ── helpers for subclasses ─────────────────────────────────────
    def _identity(self) -> str:
        return str(self.cfg.behavior.get("user_identity", "lifelong learner"))

    async def handle(self, msg: Message) -> AgentReply:  # pragma: no cover - overridden
        raise NotImplementedError
