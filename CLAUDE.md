# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**alchemist (龙虾知识炼金系统)** — a self-deployable, multi-agent knowledge system that
runs Tiago Forte's CODE methodology (Capture→Organize→Distill→Express) over a chat group
and a PARA Markdown workspace. Four bots share one workspace; the user adds them to a
Telegram group and they capture input, organize it, surface insights, and produce content.

Architecture is modeled on `nousresearch/hermes-agent` (gateway + swappable providers +
cron scheduler + YAML config), specialized into the four-agent CODE pipeline from the PRD
(`docs/龙虾知识炼金系统_产品需求文档.docx`, still the product source of truth).

## Commands

```bash
./install.sh                 # venv + install + `alchemist init`
pip install -e ".[dev]"      # dev install
pytest                       # full suite — no network needed (LLM is faked in tests)
pytest tests/test_scheduler.py::test_insight_fires_wednesday_not_tuesday   # single test

alchemist init               # create ~/.alchemist/config.yaml + PARA workspace
alchemist run                # start all bots + scheduler (the live gateway)
# token-free local testing (needs only a provider API key):
alchemist capture "text|url" # scout files it
alchemist chat <agent> "msg" # one message to scout|librarian|alchemist|publisher
alchemist draft "request"    # publisher draft
alchemist scan               # run the insight scan once
alchemist map                # run the weekly knowledge map once
```

Config lives at `~/.alchemist/config.yaml` (override with `--config` or `ALCHEMIST_CONFIG`).
**Secrets resolve from env vars and env wins over the file**: `OPENROUTER_API_KEY` /
`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, and `TELEGRAM_TOKEN_<AGENT>` (e.g. `_SCOUT`).

## Architecture (the parts that span files)

Data flows **through the filesystem, not a DB**. The PARA workspace is the single source of
truth; agents coordinate by reading/writing Markdown notes in it.

- **`workspace/`** — `Note` (one Markdown file, `YYYYMMDD-source-tag.md`, YAML front matter)
  and `Workspace` (PARA dirs). The **permission model is enforced here, not in prompts**:
  `write_note`/`append_distillation` are open to all agents; `move`/`archive` require
  `actor="librarian"` and raise otherwise (PRD §5.2).
- **`agents/`** — `base.Agent` loads the SOUL and assembles the system prompt; the four
  subclasses implement `handle(Message)`. Scheduled work lives as extra methods:
  `librarian.weekly_map()`, `alchemist.scan_insights()`. Agents return structured JSON via
  `provider.complete_json()` and the Python code performs the side effects (deterministic,
  not tool-calling loops).
- **`channels/`** — `ChatAdapter` is the platform-agnostic contract; `telegram.py` is the
  only adapter today (long-poll, one bot per agent, stdlib + httpx). `gateway.py` owns
  routing + the scheduler: **@scout listens to everything except messages addressed to
  another agent; the other three respond only when @mentioned.**
- **`providers/`** — `build_provider()` picks openrouter|anthropic|openai from config.
  `LLMProvider.complete()` is the whole surface; `complete_json()` parses JSON tolerantly.
- **`scheduler/cron.py`** — minute-tick loop, fires `weekly_map` (Mon) and `insight_push`
  (Wed/Fri), once per day, then `gateway.push()` posts into the live group.
- **`souls/*.md`, `templates/*.md`** — packaged defaults; users override per-workspace via
  `<workspace>/.souls/<agent>.md` and `<workspace>/.templates/<name>.md` (see `Agent._load_soul`
  and `PublisherAgent._load_template`).

## Design invariants (from PRD; do not violate when changing agent logic)

- **SOUL.md is the highest-priority instruction per agent**, above any chat request. It's
  injected first in every system prompt.
- **alchemist never auto-selects progressive-summary layer 3+** ("what matters most") — that
  is the user's value judgment. It does layers 1–2 and proposes; the human gate stays.
- **alchemist insight push is twice weekly, not daily** (confirmation-fatigue + settling time).
- **publisher always reverse-validates** the draft's claims before finishing.
- **One group, not four** — distinguish agents with message prefixes (`constants.PREFIX`).

## Conventions

- Python 3.10+, deps kept to `httpx` + `pyyaml` only (everything else stdlib). Keep it lean.
- Async throughout (`asyncio`); the gateway runs one poll task per bot + the scheduler.
- Tests fake the LLM (`FakeProvider`) — no network. Use `clock=` injection for time-dependent
  code (`Workspace`, `Scheduler`) rather than real `datetime.now()` in tests.

## Not yet built (PRD roadmap)

Voice transcription, more chat adapters (interface is ready), capturing insight accept/reject
from chat to feed `alchemist.record_judgment`, knowledge-map image export, multi-identity,
team/shared workspace.
