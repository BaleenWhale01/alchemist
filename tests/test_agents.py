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


@pytest.mark.asyncio
async def test_alchemist_scan_surfaces_insight_and_arms_pending(tmp_path):
    cfg = make_cfg(tmp_path)
    ws = Workspace(cfg.workspace)
    ws.init()
    for i in range(3):
        ws.write_note(Note(title=f"n{i}", body="pricing power", tags=["pricing"]))
    provider = FakeProvider(json_reply={
        "headline": "你反复在谈定价权",
        "why_it_matters": "三条笔记都绕回这点。",
        "linked_notes": ["n0", "n1"],
        "directions": ["定价权从何而来?", "如何度量?", "何时失效?"],
    })
    alch = AlchemistAgent("alchemist", cfg, provider, ws)
    reply = await alch.scan_insights()
    assert reply.skip is False
    assert alch._load_pending()["headline"] == "你反复在谈定价权"


@pytest.mark.asyncio
async def test_alchemist_reply_records_acceptance_and_clears_pending(tmp_path):
    cfg = make_cfg(tmp_path)
    ws = Workspace(cfg.workspace)
    ws.init()
    alch = AlchemistAgent("alchemist", cfg, FakeProvider(
        json_reply={"is_judgment": True, "accepted": True, "note": "定价权从何而来"}
    ), ws)
    alch._save_pending("你反复在谈定价权", ["定价权从何而来?", "如何度量?"])

    reply = await alch.handle(Message(text="1"))

    assert "记下了" in reply.rendered()
    assert alch._load_pending() is None  # consumed
    assert "你反复在谈定价权" in alch._learning_summary()
    log = (ws.root / ".alchemist" / "judgments.jsonl").read_text(encoding="utf-8")
    assert '"accepted": true' in log


@pytest.mark.asyncio
async def test_alchemist_unrelated_reply_falls_through_to_distill(tmp_path):
    cfg = make_cfg(tmp_path)
    ws = Workspace(cfg.workspace)
    ws.init()
    alch = AlchemistAgent("alchemist", cfg, FakeProvider(
        json_reply={"is_judgment": False}, text_reply="这是提炼结果"
    ), ws)
    alch._save_pending("你反复在谈定价权", ["定价权从何而来?"])

    reply = await alch.handle(Message(text="帮我提炼一下今天读的那篇文章"))

    assert reply.rendered() == "这是提炼结果"
    assert alch._load_pending() is not None  # not consumed
    assert not (ws.root / ".alchemist" / "judgments.jsonl").exists()
