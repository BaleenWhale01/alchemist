# alchemist · 龙虾知识炼金系统

A **self-deployable, multi-agent knowledge system** that runs the CODE methodology
(Capture → Organize → Distill → Express) over a chat group and a PARA Markdown
workspace. You add four bots to one chat; they turn the stuff you throw at them into
organized notes, surfaced insights, and finished content.

Architecture is modeled on [nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent):
a platform-agnostic **gateway**, swappable **LLM providers**, a **cron scheduler**, and
YAML config — specialized here into the four-agent CODE pipeline from the product PRD.

## The four agents

| Bot | CODE stage | What it does |
|-----|-----------|--------------|
| `@scout` | **Capture** | Receives everything, files it to PARA, asks at most one intent question. |
| `@librarian` | **Organize** | Guards PARA structure; the only agent that can move/archive. Pushes a weekly knowledge map. |
| `@alchemist` | **Distill** | Scans all notes for cross-note patterns; pushes insight candidates (Wed/Fri); learns your taste. |
| `@publisher` | **Express** | Turns insights + project notes into drafts (小红书/公众号/Twitter/memo/book chapter…); always reverse-validates the claims. |

All four mount the **same** PARA workspace (`Projects / Areas / Resources / Archives`).
Notes are plain Markdown (`YYYYMMDD-source-tag.md`) — yours to back up and migrate.

## Install

```bash
git clone <this repo> alchemist && cd alchemist
./install.sh
```

This creates a venv, installs the `alchemist` CLI, and runs `alchemist init` (which
writes `~/.alchemist/config.yaml` and the PARA workspace).

## Configure

Edit `~/.alchemist/config.yaml`:

1. **Provider** — default is OpenRouter. Set `provider.api_key` or export
   `OPENROUTER_API_KEY`. Switch to Anthropic/OpenAI by changing `provider.name`.
2. **Telegram** — create four bots with [@BotFather](https://t.me/BotFather), paste
   one token per agent (or use `TELEGRAM_TOKEN_SCOUT` etc.). Add all four to one group.
   **Disable @scout's privacy mode** (`/setprivacy → Disable`) so it can see every message.

Secrets can always come from environment variables instead of the file — env wins.

## Try it without Telegram

Every agent runs from the terminal with just a provider key:

```bash
alchemist capture "https://example.com/an-article"   # scout files it
alchemist chat librarian "我的知识库现在什么状态?"
alchemist chat alchemist "帮我提炼最近关于定价的笔记"
alchemist draft "@publisher 用我的知识管理笔记写第三章，主题是信息过载"
alchemist scan    # run the insight scan once
alchemist map     # generate the weekly knowledge map once
```

## Go live

```bash
alchemist run     # starts all bots + the scheduler
```

The scheduler posts the **weekly map** (Mon 9:00) and **insight candidates**
(Wed/Fri 10:00) into the group automatically. Times are configurable under `schedule:`.

### Deploy on a server

```bash
cd docker && docker compose up -d --build
```

`restart: unless-stopped` gives you the PRD's auto-restart guarantee; the `./data`
volume holds your config and workspace — back it up.

## Customize agent behavior

- **Personas**: drop a `<workspace>/.souls/<agent>.md` to override the packaged SOUL.
- **Templates**: drop a `<workspace>/.templates/<name>.md` to override/add publisher formats.
- **Models per agent**: set `agents.<id>.model` (e.g. a stronger model for `alchemist`).

## Develop

```bash
pip install -e ".[dev]"
pytest                      # full suite (no network needed)
pytest tests/test_scheduler.py::test_weekly_map_fires_monday_morning_once
```

## Project layout

```
alchemist/
  cli.py            entry point (init/run/chat/capture/draft/scan/map)
  config.py         YAML + env config
  constants.py      agent roster, PARA dirs, message prefixes
  providers/        openrouter (default) | anthropic | openai
  workspace/        PARA filesystem + Note model (permission model lives here)
  agents/           scout / librarian / alchemist / publisher
  souls/            packaged SOUL.md per agent (highest-priority instructions)
  templates/        publisher output formats
  channels/         ChatAdapter + telegram + gateway router
  scheduler/        cron-like routine runner
```

## Status

MVP (v0.5). Implemented: all four agents, PARA workspace, Telegram gateway, scheduler,
publisher templates, local CLI, and the insight accept/reject loop (replying to a pushed
insight teaches `@alchemist` your taste). Not yet: voice transcription, additional chat
platforms (the `ChatAdapter` interface is ready for them), knowledge-map image export.
See the PRD for the full roadmap.
