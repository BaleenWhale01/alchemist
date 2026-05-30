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
        "para": "Resources", "project": "", "question": "放资源库还是定价项目?",
        "title": "定价文章",
    })
    scout = ScoutAgent("scout", cfg, provider, ws)
    reply = await scout.handle(Message(text="https://example.com/pricing", kind="url"))
    assert "已接收" in reply.rendered()
    assert "放资源库还是定价项目?" in reply.rendered()
    notes = ws.all_notes()
    assert len(notes) == 1
    assert notes[0].title == "定价文章"


@pytest.mark.asyncio
async def test_alchemist_scan_skips_with_too_few_notes(tmp_path):
    cfg = make_cfg(tmp_path)
    ws = Workspace(cfg.workspace)
    ws.init()
    ws.write_note(Note(title="a", body="x", tags=["t"]))
    alch = AlchemistAgent("alchemist", cfg, FakeProvider(), ws)
    reply = await alch.scan_insights()
    assert reply.skip is True
