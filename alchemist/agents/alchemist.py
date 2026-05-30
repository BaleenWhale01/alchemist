"""@alchemist — Distill. The insight engine. Finds connections, never judges truth."""

from __future__ import annotations

import json
from pathlib import Path

from ..constants import PREFIX
from .base import Agent, AgentReply, Message

_INSIGHT_SCHEMA = """Return ONLY a JSON object:
{
  "headline": "the recurring idea / tension / hidden theme you noticed",
  "why_it_matters": "1-2 sentences, framed as observation not verdict",
  "linked_notes": ["titles of the notes that support this"],
  "directions": ["3 possible extensions, each phrased as an opening question"]
}"""


class AlchemistAgent(Agent):
    async def handle(self, msg: Message) -> AgentReply:
        """On-demand distillation: layer-1/2 summary of referenced material or a question."""
        extra = (
            "Help the user distill. Do progressive-summary layers 1 (capture essence) and "
            "2 (mark the candidate key sentences) only — never decide for them what matters "
            "most. End with a question that drives their thinking.\n\n"
            f"{self._corpus(limit=20)}"
        )
        text = await self.provider.complete(
            system=self.system_prompt(extra),
            messages=[{"role": "user", "content": msg.text}],
            model=self.model,
            temperature=0.5,
            max_tokens=900,
        )
        return AgentReply(text=text)

    async def scan_insights(self) -> AgentReply:
        """Wed/Fri routine: scan workspace, surface ONE insight candidate."""
        notes = self.ws.all_notes()
        if len(notes) < 3:
            return AgentReply(text="", skip=True)  # not enough material to connect

        extra = (
            "Scan the corpus below for ONE strong cross-note pattern: the same idea echoed "
            "across sources, a contradiction worth noting, or a hidden theme behind frequent "
            "words. Surface it as a candidate, not a verdict.\n\n"
            f"{self._learning_summary()}\n\n{self._corpus(limit=40)}\n\n{_INSIGHT_SCHEMA}"
        )
        data = await self.provider.complete_json(
            system=self.system_prompt(extra),
            messages=[{"role": "user", "content": "本周有什么值得注意的连接？"}],
            model=self.model,
            temperature=0.6,
            max_tokens=900,
        )
        dirs = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(data.get("directions", [])))
        linked = "、".join(data.get("linked_notes", [])) or "（多条笔记）"
        text = (
            f"我发现：{data.get('headline','')}\n"
            f"{data.get('why_it_matters','')}\n"
            f"关联笔记：{linked}\n"
            f"可能的方向：\n{dirs}\n"
            f"（回复方向编号告诉我哪个对你有意思，我会记住你的判断。）"
        )
        return AgentReply(text=text, prefix=PREFIX["insight"])

    def record_judgment(self, headline: str, accepted: bool, note: str = "") -> None:
        """Append the user's accept/reject so future scans learn their taste."""
        log = self._log_path()
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(
                {"headline": headline, "accepted": accepted, "note": note},
                ensure_ascii=False,
            ) + "\n")

    # ── internals ──────────────────────────────────────────────────
    def _log_path(self) -> Path:
        return self.ws.root / ".alchemist" / "judgments.jsonl"

    def _learning_summary(self) -> str:
        log = self._log_path()
        if not log.exists():
            return "User taste model: (no judgments recorded yet)"
        accepted, rejected = [], []
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                j = json.loads(line)
            except json.JSONDecodeError:
                continue
            (accepted if j.get("accepted") else rejected).append(j.get("headline", ""))
        return (
            "User taste model (lean toward the accepted, away from the rejected):\n"
            f"  accepted: {accepted[-8:] or '—'}\n"
            f"  rejected: {rejected[-8:] or '—'}"
        )

    def _corpus(self, limit: int) -> str:
        notes = self.ws.all_notes()[:limit]
        if not notes:
            return "Corpus: (empty)"
        parts = ["Corpus (title :: tags :: excerpt):"]
        for n in notes:
            excerpt = " ".join(n.body.split())[:200]
            parts.append(f"- {n.title} :: {','.join(n.tags)} :: {excerpt}")
        return "\n".join(parts)
