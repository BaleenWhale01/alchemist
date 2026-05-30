from datetime import datetime

import pytest

from alchemist.scheduler.cron import Scheduler


class FakeReply:
    skip = False
    text = "map"

    def rendered(self):
        return "map"


class FakeAgent:
    def __init__(self):
        self.calls = 0

    async def weekly_map(self):
        self.calls += 1
        return FakeReply()

    async def scan_insights(self):
        self.calls += 1
        return FakeReply()


class FakeGateway:
    def __init__(self):
        self.agents = {"librarian": FakeAgent(), "alchemist": FakeAgent()}
        self.pushed = []

    async def push(self, agent_id, reply):
        self.pushed.append(agent_id)


def make_cfg():
    class C:
        schedule = {
            "weekly_map": {"enabled": True, "day": "mon", "time": "09:00"},
            "insight_push": {"enabled": True, "days": ["wed", "fri"], "time": "10:00"},
        }
    return C()


@pytest.mark.asyncio
async def test_weekly_map_fires_monday_morning_once():
    gw = FakeGateway()
    sch = Scheduler(make_cfg(), gw)
    monday_9am = datetime(2026, 6, 1, 9, 0)   # 2026-06-01 is a Monday
    await sch.tick(monday_9am)
    await sch.tick(monday_9am)                 # same day → must not double-fire
    assert gw.pushed.count("librarian") == 1


@pytest.mark.asyncio
async def test_insight_fires_wednesday_not_tuesday():
    gw = FakeGateway()
    sch = Scheduler(make_cfg(), gw)
    tuesday = datetime(2026, 6, 2, 10, 0)
    await sch.tick(tuesday)
    assert "alchemist" not in gw.pushed
    wednesday = datetime(2026, 6, 3, 10, 0)
    await sch.tick(wednesday)
    assert gw.pushed.count("alchemist") == 1


@pytest.mark.asyncio
async def test_not_due_before_time():
    gw = FakeGateway()
    sch = Scheduler(make_cfg(), gw)
    monday_early = datetime(2026, 6, 1, 8, 59)
    await sch.tick(monday_early)
    assert gw.pushed == []
