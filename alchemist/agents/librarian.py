"""@librarian — Organize. PARA guardian; the only agent that may move/archive."""

from __future__ import annotations

from ..constants import PREFIX
from .base import Agent, AgentReply, Message


class LibrarianAgent(Agent):
    async def handle(self, msg: Message) -> AgentReply:
        extra = (
            "Answer the user's organizing question, or suggest a migration "
            "(Resource→Project) when their message references a Resource that relates "
            "to an active Project. Suggest moves; do not claim you moved anything unless "
            "the user explicitly told you to. Be brief.\n\n"
            f"{self._inventory()}"
        )
        text = await self.provider.complete(
            system=self.system_prompt(extra),
            messages=[{"role": "user", "content": msg.text}],
            model=self.model,
            temperature=0.3,
            max_tokens=700,
        )
        return AgentReply(text=text)

    async def weekly_map(self) -> AgentReply:
        """Monday routine: scan the whole library, push the weekly knowledge map."""
        extra = (
            "Produce this week's KNOWLEDGE MAP from the inventory below. Sections:\n"
            "1) Active Projects (in progress)\n"
            "2) Resources worth attention (worth using or migrating)\n"
            "3) Suggested to Archive (no longer active)\n"
            "Keep it scannable: short bullets, name concrete notes. End with one "
            "prompting question about what to focus on next week.\n\n"
            f"{self._inventory(full=True)}"
        )
        text = await self.provider.complete(
            system=self.system_prompt(extra),
            messages=[{"role": "user", "content": "Generate this week's knowledge map."}],
            model=self.model,
            temperature=0.4,
            max_tokens=1200,
        )
        return AgentReply(text=text, prefix=PREFIX["weekly_map"])

    def _inventory(self, full: bool = False) -> str:
        notes = self.ws.all_notes()
        if not notes:
            return "Workspace inventory: (empty)"
        by_para: dict[str, list[str]] = {}
        for n in notes:
            label = n.title + (f" [{n.project}]" if n.project else "")
            by_para.setdefault(n.para, []).append(label)
        lines = [f"Workspace inventory ({len(notes)} notes):"]
        for para, items in by_para.items():
            shown = items if full else items[:12]
            lines.append(f"- {para} ({len(items)}): " + "; ".join(shown))
        return "\n".join(lines)
