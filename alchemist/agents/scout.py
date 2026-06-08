"""@scout — Capture. Receives everything, files it, asks at most one question."""

from __future__ import annotations

from ..constants import PREFIX
from ..workspace import Note
from .base import Agent, AgentReply, Message

_SCHEMA = """Return ONLY a JSON object:
{
  "summary": "one-line core of the content",
  "kind": "text|url|image|voice|file",
  "tags": ["1-3 short tags"],
  "para": "Projects|Areas|Resources|Archives",
  "project": "project name if para==Projects else \\"\\"",
  "question": "at most ONE short intent question, or \\"\\" if placement is obvious",
  "title": "a short title for the note"
}"""


class ScoutAgent(Agent):
    async def handle(self, msg: Message) -> AgentReply:
        active_projects = self._active_projects()
        extra = (
            f"Active projects the user has: {active_projects or '(none yet)'}.\n"
            f"Decide where this capture belongs. Default to Resources when unsure.\n{_SCHEMA}"
        )
        decision = await self.provider.complete_json(
            system=self.system_prompt(extra),
            messages=[{"role": "user", "content": msg.text}],
            model=self.model,
            temperature=0.2,
            max_tokens=600,
        )

        note = Note(
            title=decision.get("title") or (decision.get("summary") or msg.text)[:40],
            body=msg.text,
            source=decision.get("kind", msg.kind or "chat"),
            tags=list(decision.get("tags", []) or []),
            para=decision.get("para", "Resources"),
            project=decision.get("project", "") or "",
        )
        path = self.ws.write_note(note)

        loc = f"{note.para}/{note.project}".rstrip("/")
        tags = ", ".join(note.tags) if note.tags else "none"
        confirm = f"Captured: \"{note.title}\" → {loc} (tags: {tags})"
        question = (decision.get("question") or "").strip()
        if question:
            confirm += f"\n{question}"
        return AgentReply(text=confirm, prefix=PREFIX["capture"])

    def _active_projects(self) -> list[str]:
        proj_dir = self.ws.root / "Projects"
        if not proj_dir.exists():
            return []
        return [p.name for p in proj_dir.iterdir() if p.is_dir()]
