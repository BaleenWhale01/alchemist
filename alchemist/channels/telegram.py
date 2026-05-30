"""Telegram adapter — one bot per agent, via long-poll getUpdates (no extra deps).

For @scout to receive *all* group messages, disable its bot's privacy mode in
@BotFather (/setprivacy → Disable). The other three only need messages that mention
them, so their privacy mode can stay on.
"""

from __future__ import annotations

import asyncio
import logging

import httpx

from .base import ChatAdapter, Handler, Incoming

log = logging.getLogger("alchemist.telegram")


class TelegramAdapter(ChatAdapter):
    API = "https://api.telegram.org"

    def __init__(self, agent_id: str, token: str, group_id: str = ""):
        self.agent_id = agent_id
        self.token = token
        self.group_id = str(group_id or "")
        self._username = ""
        self._offset = 0

    def _url(self, method: str) -> str:
        return f"{self.API}/bot{self.token}/{method}"

    async def whoami(self) -> str:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(self._url("getMe"))
            r.raise_for_status()
            self._username = r.json()["result"].get("username", self.agent_id)
        return self._username

    async def send(self, chat_id: str, text: str) -> None:
        # Telegram caps messages at 4096 chars; chunk if needed.
        async with httpx.AsyncClient(timeout=60) as c:
            for chunk in _chunks(text, 4000):
                r = await c.post(self._url("sendMessage"), json={"chat_id": chat_id, "text": chunk})
                if r.status_code != 200:
                    log.warning("[%s] sendMessage failed: %s", self.agent_id, r.text)

    async def run(self, handler: Handler) -> None:
        if not self._username:
            await self.whoami()
        log.info("[%s] polling as @%s", self.agent_id, self._username)
        async with httpx.AsyncClient(timeout=70) as c:
            while True:
                try:
                    r = await c.get(
                        self._url("getUpdates"),
                        params={"offset": self._offset, "timeout": 50},
                    )
                    r.raise_for_status()
                    for upd in r.json().get("result", []):
                        self._offset = upd["update_id"] + 1
                        inc = self._parse(upd)
                        if inc:
                            await handler(self.agent_id, inc)
                except httpx.HTTPError as e:
                    log.warning("[%s] poll error: %s; retrying in 3s", self.agent_id, e)
                    await asyncio.sleep(3)

    def _parse(self, upd: dict) -> Incoming | None:
        msg = upd.get("message") or upd.get("channel_post")
        if not msg:
            return None
        chat_id = str(msg.get("chat", {}).get("id", ""))
        if self.group_id and chat_id != self.group_id:
            return None
        sender = (msg.get("from", {}) or {}).get("username") or str(
            (msg.get("from", {}) or {}).get("id", "user")
        )
        kind, text = _kind_and_text(msg)
        if not text:
            return None
        return Incoming(chat_id=chat_id, text=text, sender=sender, kind=kind)


def _kind_and_text(msg: dict) -> tuple[str, str]:
    if "text" in msg:
        text = msg["text"]
        kind = "url" if text.strip().startswith(("http://", "https://")) else "text"
        return kind, text
    if "caption" in msg and ("photo" in msg or "document" in msg):
        return ("image" if "photo" in msg else "file"), msg["caption"]
    if "voice" in msg:
        return "voice", "[语音消息 — 转写功能见 v1.1]"
    if "photo" in msg:
        return "image", "[图片]"
    if "document" in msg:
        return "file", "[文件：%s]" % msg["document"].get("file_name", "")
    return "text", ""


def _chunks(text: str, n: int):
    for i in range(0, len(text), n):
        yield text[i : i + n]
