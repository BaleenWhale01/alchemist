"""Chat-platform adapter contract.

Adding a platform (Discord/Slack/…) means implementing this interface and registering
it in the Gateway. The gateway is platform-agnostic: it only speaks Incoming/send.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass
class Incoming:
    chat_id: str
    text: str
    sender: str = "user"
    kind: str = "text"        # text | url | image | voice | file


# handler(agent_id, Incoming) -> awaitable; the gateway provides it per bot.
Handler = Callable[[str, Incoming], Awaitable[None]]


class ChatAdapter(ABC):
    """One running bot connection bound to a single agent id."""

    agent_id: str

    @abstractmethod
    async def whoami(self) -> str:
        """Return the bot's handle/username (used for mention detection)."""

    @abstractmethod
    async def run(self, handler: Handler) -> None:
        """Long-running receive loop; call handler for each inbound message."""

    @abstractmethod
    async def send(self, chat_id: str, text: str) -> None:
        ...
