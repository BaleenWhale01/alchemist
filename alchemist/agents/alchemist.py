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

_JUDGMENT_SCHEMA = """You just pushed this insight candidate to the user:
  headline: {headline}
  directions:
{dirs}
Their message below is a REPLY in the same chat. Decide whether it is a reaction to that
candidate — picking/endorsing a direction (acceptance) or dismissing it (rejection) — as
opposed to an unrelated new request. When unsure, treat it as NOT a judgment.
Return ONLY a JSON object:
{{
  "is_judgment": true or false,
  "accepted": true or false,
  "note": "if accepted, the direction/angle they liked; if rejected, a short why. else empty"
}}"""


class AlchemistAgent(Agent):
    async def handle(self, msg: Message) -> AgentReply:
        """On-demand distillation — but first, if an insight is awaiting the user's verdict,
        interpret this reply as that accept/reject and record it (the taste-learning loop)."""
        pending = self._load_pending()
        if pending:
            verdict = await self._classify_judgment(msg.text, pending)
            if verdict.get("is_judgment"):
                accepted = bool(verdict.get("accepted"))
                head = pending.get("headline", "")
                self.record_judgment(head, accepted, str(verdict.get("note", "")))
                self._clear_pending()
                if accepted:
                    return AgentReply(
                        text=f"Noted — you're into the \"{head}\" direction; I'll lean toward connections like this from now on."
                    )
                return AgentReply(text=f"Okay, I'll set \"{head}\" aside and try a different angle next time.")

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
            messages=[{"role": "user", "content": "What connections are worth noticing this week?"}],
            model=self.model,
            temperature=0.6,
            max_tokens=900,
        )
        dirs = "\n".join(f"  {i+1}. {d}" for i, d in enumerate(data.get("directions", [])))
        linked = ", ".join(data.get("linked_notes", [])) or "(several notes)"
        text = (
            f"I noticed: {data.get('headline','')}\n"
            f"{data.get('why_it_matters','')}\n"
            f"Linked notes: {linked}\n"
            f"Possible directions:\n{dirs}\n"
            f"(Reply with a direction number to tell me which interests you — I'll remember your judgment.)"
        )
        self._save_pending(data.get("headline", ""), data.get("directions", []))
        return AgentReply(text=text, prefix=PREFIX["insight"])

    async def _classify_judgment(self, text: str, pending: dict) -> dict:
        """Ask the model whether `text` is the user's accept/reject of the pending insight."""
        dirs = "\n".join(
            f"  {i+1}. {d}" for i, d in enumerate(pending.get("directions", []))
        ) or "  (none)"
        schema = _JUDGMENT_SCHEMA.format(headline=pending.get("headline", ""), dirs=dirs)
        return await self.provider.complete_json(
            system=self.system_prompt(schema),
            messages=[{"role": "user", "content": text}],
            model=self.model,
            temperature=0,
            max_tokens=200,
        )

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

    def _pending_path(self) -> Path:
        return self.ws.root / ".alchemist" / "pending.json"

    def _save_pending(self, headline: str, directions: list) -> None:
        p = self._pending_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps({"headline": headline, "directions": directions}, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_pending(self) -> dict | None:
        p = self._pending_path()
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _clear_pending(self) -> None:
        self._pending_path().unlink(missing_ok=True)

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
