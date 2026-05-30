"""The four CODE agents."""

from __future__ import annotations

from ..config import Config
from ..providers import LLMProvider
from ..workspace import Workspace
from .alchemist import AlchemistAgent
from .base import Agent, AgentReply
from .librarian import LibrarianAgent
from .publisher import PublisherAgent
from .scout import ScoutAgent

_REGISTRY = {
    "scout": ScoutAgent,
    "librarian": LibrarianAgent,
    "alchemist": AlchemistAgent,
    "publisher": PublisherAgent,
}


def build_agents(cfg: Config, provider: LLMProvider, ws: Workspace) -> dict[str, Agent]:
    return {aid: cls(aid, cfg, provider, ws) for aid, cls in _REGISTRY.items()}


__all__ = [
    "Agent",
    "AgentReply",
    "ScoutAgent",
    "LibrarianAgent",
    "AlchemistAgent",
    "PublisherAgent",
    "build_agents",
]
