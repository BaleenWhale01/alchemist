"""The Note model: one Markdown file per captured item.

Filename convention (PRD §5.2): ``YYYYMMDD-source-tag.md``.
Each note carries YAML front matter so agents can read structured metadata
without re-parsing prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml

_SLUG_RE = re.compile(r"[^0-9a-zA-Z]+")


def slugify(text: str, max_len: int = 24) -> str:
    s = _SLUG_RE.sub("-", (text or "").strip()).strip("-")
    return (s or "untitled")[:max_len]


@dataclass
class Note:
    title: str
    body: str
    source: str = "chat"           # url | image | voice | file | chat
    tags: list[str] = field(default_factory=list)
    para: str = "Resources"        # Projects | Areas | Resources | Archives
    project: str = ""              # subfolder under Projects/ when para == Projects
    created: str = ""              # YYYY-MM-DD HH:MM (filled at write time if blank)
    path: Path | None = None       # set once persisted

    def filename(self, when: datetime) -> str:
        date = when.strftime("%Y%m%d")
        src = slugify(self.source, 12)
        tag = slugify(self.tags[0] if self.tags else self.title, 24)
        return f"{date}-{src}-{tag}.md"

    def to_markdown(self) -> str:
        meta = {
            "title": self.title,
            "source": self.source,
            "tags": self.tags,
            "para": self.para,
            "project": self.project,
            "created": self.created,
        }
        front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
        return f"---\n{front}\n---\n\n# {self.title}\n\n{self.body.strip()}\n"

    @classmethod
    def from_file(cls, path: Path) -> "Note":
        text = path.read_text(encoding="utf-8")
        meta: dict = {}
        body = text
        if text.startswith("---"):
            _, _, rest = text.partition("---")
            front, sep, body = rest.partition("---")
            if sep:
                meta = yaml.safe_load(front) or {}
        note = cls(
            title=meta.get("title", path.stem),
            body=body.strip(),
            source=meta.get("source", "chat"),
            tags=list(meta.get("tags", []) or []),
            para=meta.get("para", "Resources"),
            project=meta.get("project", ""),
            created=meta.get("created", ""),
        )
        note.path = path
        return note
