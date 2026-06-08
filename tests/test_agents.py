import pytest

from alchemist.agents.alchemist import AlchemistAgent
from alchemist.agents.base import Message
from alchemist.agents.scout import ScoutAgent
from alchemist.config import Config
from alchemist.workspace import Note, Workspace


class FakeProvider:
    def __init__(self, json_reply=None, text_reply="ok"):
        self._json = json_reply or {}
        self._text = text_reply

    async def complete(self, **kwargs):
        return self._text

    async def complete_json(self, **kwargs):
        return self._json


def make_cfg(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "workspace: {ws}\nprovider:\n  name: openrouter\n  model: m\n".format(ws=tmp_path / "ws"),
        encoding="utf-8",
    )
    return Config.load(str(cfg_file))


@pytest.mark.asyncio
async def test_scout_captures_to_workspace(tmp_path):
    cfg = make_cfg(tmp_path)
    ws = Workspace(cfg.workspace)
    ws.init()
    provider = FakeProvider(json_reply={
        "summary": "value-based pricing", "kind": "url", "tags": ["pricing"],
        "para": "Resources", "project": "", "question": "Resources or the Pricing project?",
        "title": "Pricing article",
    })
    scout = ScoutAgent("scout", cfg, provider, ws)
    reply = await scout.handle(Message(text="https://example.com/pricing", kind="url"))
    assert "Captured" in reply.rendered()
    assert "Resources or the Pricing project?" in reply.rendered()
    notes = ws.all_notes()
    assert len(notes) == 1
    assert notes[0].title == "Pricing article"


@pytest.mark.asyncio
async def test_alchemist_scan_skips_with_too_few_notes(tmp_path):
    cfg = make_cfg(tmp_path)
    ws = Workspace(cfg.workspace)
    ws.init()
    ws.write_note(Note(title="a", body="x", tags=["t"]))
    alch = AlchemistAgent("alchemist", cfg, FakeProvider(), ws)
    reply = await alch.scan_insights()
    assert reply.skip is True


@pytest.mark.asyncio
async def test_alchemist_scan_surfaces_insight_and_arms_pending(tmp_path):
    cfg = make_cfg(tmp_path)
    ws = Workspace(cfg.workspace)
    ws.init()
    for i in range(3):
        ws.write_note(Note(title=f"n{i}", body="pricing power", tags=["pricing"]))
    provider = FakeProvider(json_reply={
        "headline": "You keep returning to pricing power",
        "why_it_matters": "All three notes circle back to it.",
        "linked_notes": ["n0", "n1"],
        "directions": ["Where does pricing power come from?", "How do you measure it?", "When does it break down?"],
    })
    alch = AlchemistAgent("alchemist", cfg, provider, ws)
    reply = await alch.scan_insights()
    assert reply.skip is False
    assert alch._load_pending()["headline"] == "You keep returning to pricing power"


@pytest.mark.asyncio
async def test_alchemist_reply_records_acceptance_and_clears_pending(tmp_path):
    cfg = make_cfg(tmp_path)
    ws = Workspace(cfg.workspace)
    ws.init()
    alch = AlchemistAgent("alchemist", cfg, FakeProvider(
        json_reply={"is_judgment": True, "accepted": True, "note": "where pricing power comes from"}
    ), ws)
    alch._save_pending("You keep returning to pricing power", ["Where does pricing power come from?", "How do you measure it?"])

    reply = await alch.handle(Message(text="1"))

    assert "Noted" in reply.rendered()
    assert alch._load_pending() is None  # consumed
    assert "You keep returning to pricing power" in alch._learning_summary()
    log = (ws.root / ".alchemist" / "judgments.jsonl").read_text(encoding="utf-8")
    assert '"accepted": true' in log


@pytest.mark.asyncio
async def test_alchemist_unrelated_reply_falls_through_to_distill(tmp_path):
    cfg = make_cfg(tmp_path)
    ws = Workspace(cfg.workspace)
    ws.init()
    alch = AlchemistAgent("alchemist", cfg, FakeProvider(
        json_reply={"is_judgment": False}, text_reply="Here is the distillation"
    ), ws)
    alch._save_pending("You keep returning to pricing power", ["Where does pricing power come from?"])

    reply = await alch.handle(Message(text="Help me distill the article I read today"))

    assert reply.rendered() == "Here is the distillation"
    assert alch._load_pending() is not None  # not consumed
    assert not (ws.root / ".alchemist" / "judgments.jsonl").exists()
