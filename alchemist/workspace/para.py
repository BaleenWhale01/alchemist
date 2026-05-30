"""The PARA workspace — the shared filesystem that is the system's source of truth.

Permission model (PRD §5.2): librarian may move/rename/delete; every other agent
is append-only. That contract is enforced here, not left to agent prompts:
``write_note`` / ``append`` are open to all, while ``move`` / ``archive`` require
``actor="librarian"``.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from ..constants import DISTILL_MARKER, PARA_DIRS
from .note import Note


class PermissionError_(PermissionError):
    """Raised when a non-librarian agent attempts a structural mutation."""


class Workspace:
    def __init__(self, root: Path, clock: Callable[[], datetime] = datetime.now):
        self.root = Path(root)
        self._clock = clock

    # ── lifecycle ──────────────────────────────────────────────────
    def init(self) -> None:
        for d in PARA_DIRS:
            (self.root / d).mkdir(parents=True, exist_ok=True)

    def _dir_for(self, note: Note) -> Path:
        if note.para == "Projects" and note.project:
            return self.root / "Projects" / note.project
        return self.root / note.para

    # ── create / read (open to all agents) ─────────────────────────
    def write_note(self, note: Note) -> Path:
        if not note.created:
            note.created = self._clock().strftime("%Y-%m-%d %H:%M")
        target_dir = self._dir_for(note)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / note.filename(self._clock())
        # avoid clobbering a same-named capture from the same day
        n = 1
        while path.exists():
            path = target_dir / f"{path.stem}-{n}.md"
            n += 1
        path.write_text(note.to_markdown(), encoding="utf-8")
        note.path = path
        return path

    def all_notes(self) -> list[Note]:
        notes: list[Note] = []
        for md in self.root.rglob("*.md"):
            if md.name.upper() == "SOUL.MD":
                continue
            try:
                notes.append(Note.from_file(md))
            except Exception:
                continue
        return notes

    def notes_in(self, para: str, project: str = "") -> list[Note]:
        base = self.root / para / project if project else self.root / para
        if not base.exists():
            return []
        return [Note.from_file(p) for p in base.rglob("*.md") if p.name.upper() != "SOUL.MD"]

    # ── append (open to all; used by alchemist for distillation) ────
    def append_distillation(self, note: Note, content: str) -> None:
        if not note.path:
            raise ValueError("note has no path; persist it first")
        with note.path.open("a", encoding="utf-8") as f:
            f.write(f"\n\n{DISTILL_MARKER}\n{content.strip()}\n")

    # ── structural mutation (librarian only) ───────────────────────
    def move(self, note: Note, *, para: str, project: str = "", actor: str = "") -> Path:
        if actor != "librarian":
            raise PermissionError_(f"{actor or 'agent'} may not move notes; only librarian can.")
        if not note.path:
            raise ValueError("note has no path")
        note.para, note.project = para, project
        dest_dir = self._dir_for(note)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / note.path.name
        note.path.rename(dest)
        note.path = dest
        # keep front matter in sync with new location
        dest.write_text(note.to_markdown(), encoding="utf-8")
        return dest

    def archive(self, note: Note, *, actor: str = "") -> Path:
        return self.move(note, para="Archives", actor=actor)

    # ── publisher drafts ───────────────────────────────────────────
    def save_draft(self, project: str, title: str, content: str) -> Path:
        from .note import slugify

        ddir = self.root / "Projects" / (project or "uncategorized") / "drafts"
        ddir.mkdir(parents=True, exist_ok=True)
        stamp = self._clock().strftime("%Y%m%d-%H%M")
        path = ddir / f"{stamp}-{slugify(title)}.md"
        path.write_text(content, encoding="utf-8")
        return path
