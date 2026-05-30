"""Lightweight time-of-day scheduler for the two PRD routines.

A minute-resolution loop (no external cron dep) checks each enabled job against the
local clock and fires once per matching day. The PRD allows ±10min slack, which a
60s tick comfortably meets.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Callable

log = logging.getLogger("alchemist.scheduler")

_DAYS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


class Scheduler:
    def __init__(self, cfg, gateway, clock: Callable[[], datetime] = datetime.now):
        self.cfg = cfg
        self.gw = gateway
        self._clock = clock
        self._fired: dict[str, str] = {}   # job -> last YYYY-MM-DD it ran

    def _jobs(self) -> list[dict]:
        sch = self.cfg.schedule or {}
        jobs = []
        wm = sch.get("weekly_map", {})
        if wm.get("enabled", True):
            jobs.append({
                "name": "weekly_map", "agent": "librarian", "method": "weekly_map",
                "days": [wm.get("day", "mon")], "time": wm.get("time", "09:00"),
            })
        ip = sch.get("insight_push", {})
        if ip.get("enabled", True):
            jobs.append({
                "name": "insight_push", "agent": "alchemist", "method": "scan_insights",
                "days": ip.get("days", ["wed", "fri"]), "time": ip.get("time", "10:00"),
            })
        return jobs

    async def run(self) -> None:
        log.info("scheduler started (%d jobs)", len(self._jobs()))
        while True:
            await self.tick(self._clock())
            await asyncio.sleep(60)

    async def tick(self, now: datetime) -> None:
        today = now.strftime("%Y-%m-%d")
        for job in self._jobs():
            if self._fired.get(job["name"]) == today:
                continue
            if not self._due(job, now):
                continue
            self._fired[job["name"]] = today
            await self._fire(job)

    def _due(self, job: dict, now: datetime) -> bool:
        wanted_days = {_DAYS.get(d.lower(), -1) for d in job["days"]}
        if now.weekday() not in wanted_days:
            return False
        try:
            hh, mm = (int(x) for x in job["time"].split(":"))
        except ValueError:
            return False
        # fire when we've reached the scheduled minute (and not yet fired today)
        return (now.hour, now.minute) >= (hh, mm)

    async def _fire(self, job: dict) -> None:
        log.info("firing routine: %s", job["name"])
        agent = self.gw.agents[job["agent"]]
        try:
            reply = await getattr(agent, job["method"])()
        except Exception:
            log.exception("routine %s failed", job["name"])
            return
        await self.gw.push(job["agent"], reply)
