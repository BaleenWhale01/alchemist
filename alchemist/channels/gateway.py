"""The gateway: routes inbound chat messages to the right agent and runs routines.

Routing rules (PRD §2.2):
- @scout listens to everything (requireMention=false) EXCEPT messages clearly addressed
  to another agent (so it doesn't capture commands as notes).
- librarian / alchemist / publisher respond ONLY when @mentioned.

One bot connection per agent. The same Gateway also owns the scheduler so routines
(weekly map, insight push) post into the live group chat.
"""

from __future__ import annotations

import asyncio
import logging
import re

from ..agents import build_agents
from ..agents.base import Message
from ..config import Config
from ..constants import AGENTS
from ..providers import LLMProvider
from ..workspace import Workspace
from .base import Incoming
from .telegram import TelegramAdapter

log = logging.getLogger("alchemist.gateway")


class Gateway:
    def __init__(self, cfg: Config, provider: LLMProvider, ws: Workspace):
        self.cfg = cfg
        self.agents = build_agents(cfg, provider, ws)
        self.adapters: dict[str, TelegramAdapter] = {}
        self.mentions: dict[str, set[str]] = {}      # agent_id -> mention tokens
        self.group_chat_id: str = cfg.telegram.group_id or ""

        if cfg.telegram.enabled:
            for aid in AGENTS:
                token = cfg.telegram.token_for(aid)
                if token:
                    self.adapters[aid] = TelegramAdapter(aid, token, cfg.telegram.group_id)
                else:
                    log.warning("no telegram token for @%s; that agent is offline", aid)

    async def run(self) -> None:
        if not self.adapters:
            raise RuntimeError(
                "No chat adapters configured. Add telegram bot tokens to your config "
                "(or set TELEGRAM_TOKEN_SCOUT etc.)."
            )
        # resolve usernames → mention tokens
        for aid, ad in self.adapters.items():
            username = await ad.whoami()
            self.mentions[aid] = {f"@{aid}", f"@{username}".lower(), aid}

        from ..scheduler.cron import Scheduler

        scheduler = Scheduler(self.cfg, self)
        tasks = [asyncio.create_task(ad.run(self._handle)) for ad in self.adapters.values()]
        tasks.append(asyncio.create_task(scheduler.run()))
        log.info("gateway up: %s", ", ".join(f"@{a}" for a in self.adapters))
        await asyncio.gather(*tasks)

    # ── routing ────────────────────────────────────────────────────
    async def _handle(self, agent_id: str, inc: Incoming) -> None:
        if not self.group_chat_id:
            self.group_chat_id = inc.chat_id  # adopt the first group we see

        text = inc.text
        addressed = self._addressed_agent(text)

        if agent_id == "scout":
            # scout captures everything not aimed at another agent
            if addressed and addressed != "scout":
                return
            await self._dispatch("scout", inc, self._strip_mentions(text))
            return

        # mention-gated agents
        if addressed == agent_id or self._mentions_me(agent_id, text):
            await self._dispatch(agent_id, inc, self._strip_mentions(text))

    async def _dispatch(self, agent_id: str, inc: Incoming, clean_text: str) -> None:
        agent = self.agents[agent_id]
        try:
            reply = await agent.handle(
                Message(text=clean_text or inc.text, sender=inc.sender,
                        chat_id=inc.chat_id, kind=inc.kind)
            )
        except Exception as e:  # never let one bad message kill the poller
            log.exception("[%s] handler error", agent_id)
            await self.adapters[agent_id].send(inc.chat_id, f"⚠️ @{agent_id} hit an error: {e}")
            return
        if reply.skip or not reply.text.strip():
            return
        await self.adapters[agent_id].send(inc.chat_id, reply.rendered())

    async def push(self, agent_id: str, reply) -> None:
        """Used by the scheduler to post a routine into the group."""
        if reply.skip or not reply.text.strip():
            return
        if not self.group_chat_id:
            log.warning("no group chat id yet; skipping scheduled push from @%s", agent_id)
            return
        if agent_id not in self.adapters:
            return
        await self.adapters[agent_id].send(self.group_chat_id, reply.rendered())

    # ── mention helpers ────────────────────────────────────────────
    def _mentions_me(self, agent_id: str, text: str) -> bool:
        low = text.lower()
        return any(tok in low for tok in self.mentions.get(agent_id, set()))

    def _addressed_agent(self, text: str) -> str:
        """If the message starts with @<agent>, return that agent id, else ''."""
        m = re.match(r"\s*@([A-Za-z0-9_]+)", text)
        if not m:
            return ""
        handle = "@" + m.group(1).lower()
        for aid, toks in self.mentions.items():
            if handle in toks or m.group(1).lower() == aid:
                return aid
        return ""

    @staticmethod
    def _strip_mentions(text: str) -> str:
        return re.sub(r"@[A-Za-z0-9_]+", "", text).strip()
