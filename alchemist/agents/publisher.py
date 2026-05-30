"""@publisher — Express. Turns distillations + project notes into a draft."""

from __future__ import annotations

from importlib import resources

from ..constants import PREFIX
from .base import Agent, AgentReply, Message

# user-facing names / aliases → template file stem
_TEMPLATES = {
    "xiaohongshu": "xiaohongshu", "小红书": "xiaohongshu",
    "wechat": "wechat", "公众号": "wechat",
    "twitter": "twitter_thread", "x": "twitter_thread", "thread": "twitter_thread",
    "memo": "decision_memo", "决策": "decision_memo", "决策备忘录": "decision_memo",
    "book": "book_chapter", "书稿": "book_chapter", "章节": "book_chapter",
}

# default template per user identity
_IDENTITY_DEFAULT = {
    "blogger": "xiaohongshu", "自媒体": "xiaohongshu", "博主": "xiaohongshu",
    "founder": "decision_memo", "创业者": "decision_memo",
    "expert": "book_chapter", "author": "book_chapter", "专家": "book_chapter", "作者": "book_chapter",
}


class PublisherAgent(Agent):
    async def handle(self, msg: Message) -> AgentReply:
        template_key = self._pick_template(msg.text)
        template = self._load_template(template_key)
        project = self._guess_project(msg.text)
        material = self._material(project)

        extra = (
            "First confirm the thesis is clear from the request; then generate the draft "
            "following the template. After the draft, ALWAYS append a reverse-validation "
            "block: count the core claims and ask how many have a concrete case/evidence, "
            "naming any unsupported one.\n\n"
            f"===== TEMPLATE: {template_key} =====\n{template}\n\n"
            f"===== MATERIAL (project: {project or 'n/a'}) =====\n{material}"
        )
        draft = await self.provider.complete(
            system=self.system_prompt(extra),
            messages=[{"role": "user", "content": msg.text}],
            model=self.model,
            temperature=0.6,
            max_tokens=2400,
        )
        title = msg.text[:40]
        path = self.ws.save_draft(project, title, draft)
        footer = f"\n\n———\n草稿已存入 {path.relative_to(self.ws.root)}"
        return AgentReply(text=draft + footer, prefix=PREFIX["draft"])

    # ── internals ──────────────────────────────────────────────────
    def _pick_template(self, text: str) -> str:
        low = text.lower()
        for alias, stem in _TEMPLATES.items():
            if alias in low or alias in text:
                return stem
        configured = self.cfg.behavior.get("publisher_default_template")
        if configured:
            return configured
        return _IDENTITY_DEFAULT.get(self._identity().lower(), "wechat")

    def _load_template(self, stem: str) -> str:
        override = self.ws.root / ".templates" / f"{stem}.md"
        if override.exists():
            return override.read_text(encoding="utf-8")
        try:
            return resources.files("alchemist.templates").joinpath(f"{stem}.md").read_text(
                encoding="utf-8"
            )
        except (FileNotFoundError, ModuleNotFoundError):
            return f"(no template found for {stem}; write a well-structured piece.)"

    def _guess_project(self, text: str) -> str:
        proj_dir = self.ws.root / "Projects"
        if not proj_dir.exists():
            return ""
        for p in proj_dir.iterdir():
            if p.is_dir() and p.name in text:
                return p.name
        # fall back to first active project, if any
        dirs = [p.name for p in proj_dir.iterdir() if p.is_dir()]
        return dirs[0] if dirs else ""

    def _material(self, project: str) -> str:
        notes = self.ws.notes_in("Projects", project) if project else self.ws.all_notes()[:15]
        if not notes:
            return "(no project notes found; draft from the request alone and flag the gap.)"
        parts = []
        for n in notes:
            parts.append(f"## {n.title}\n{n.body[:1200]}")
        return "\n\n".join(parts)
