from datetime import datetime

import pytest

from alchemist.workspace import Note, Workspace
from alchemist.workspace.para import PermissionError_


def fixed_clock():
    return datetime(2026, 5, 30, 9, 0)


def test_write_and_read_note(tmp_path):
    ws = Workspace(tmp_path, clock=fixed_clock)
    ws.init()
    note = Note(title="Pricing strategy", body="Price by value, not cost", source="url", tags=["pricing"], para="Resources")
    path = ws.write_note(note)
    assert path.exists()
    assert path.name == "20260530-url-pricing.md"
    loaded = Note.from_file(path)
    assert loaded.title == "Pricing strategy"
    assert loaded.tags == ["pricing"]
    assert loaded.para == "Resources"


def test_filename_collision_suffixes(tmp_path):
    ws = Workspace(tmp_path, clock=fixed_clock)
    ws.init()
    a = ws.write_note(Note(title="x", body="1", source="url", tags=["t"]))
    b = ws.write_note(Note(title="x", body="2", source="url", tags=["t"]))
    assert a != b


def test_only_librarian_can_move(tmp_path):
    ws = Workspace(tmp_path, clock=fixed_clock)
    ws.init()
    note = Note(title="idea", body="...", tags=["t"], para="Resources")
    ws.write_note(note)
    with pytest.raises(PermissionError_):
        ws.move(note, para="Projects", project="book", actor="scout")
    dest = ws.move(note, para="Projects", project="book", actor="librarian")
    assert "Projects/book" in str(dest)
    assert dest.exists()


def test_append_distillation(tmp_path):
    ws = Workspace(tmp_path, clock=fixed_clock)
    ws.init()
    note = Note(title="n", body="body", tags=["t"])
    ws.write_note(note)
    ws.append_distillation(note, "**key sentence**")
    text = note.path.read_text(encoding="utf-8")
    assert "--- Distilled ---" in text
    assert "**key sentence**" in text


def test_save_draft(tmp_path):
    ws = Workspace(tmp_path, clock=fixed_clock)
    ws.init()
    path = ws.save_draft("book", "Chapter 3", "draft content")
    assert path.exists()
    assert "Projects/book/drafts" in str(path)
