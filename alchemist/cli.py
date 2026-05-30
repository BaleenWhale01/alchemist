"""alchemist command-line entry point.

    alchemist init                 # create workspace + config
    alchemist run                  # start the gateway (chat bots + scheduler)
    alchemist chat <agent> "msg"   # talk to one agent locally (no chat platform needed)
    alchemist capture "text"       # scout-capture something from the terminal
    alchemist draft "request"      # publisher draft from the terminal
    alchemist scan                 # run the alchemist insight scan once, print result
    alchemist map                  # run the librarian weekly map once, print result

The `chat/capture/draft/scan/map` commands need only a provider API key — handy for
trying the system before wiring up Telegram bots.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import sys
from importlib import resources
from pathlib import Path

from .agents.base import Message
from .config import Config
from .constants import AGENTS, DEFAULT_CONFIG_PATH


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _build_runtime(cfg: Config):
    from .providers import build_provider
    from .workspace import Workspace

    ws = Workspace(cfg.workspace)
    provider = build_provider(cfg.provider)
    from .agents import build_agents

    return ws, provider, build_agents(cfg, provider, ws)


# ── commands ───────────────────────────────────────────────────────
def cmd_init(args) -> int:
    from .workspace import Workspace

    cfg_path = Path(args.config or DEFAULT_CONFIG_PATH).expanduser()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    if not cfg_path.exists():
        example = _find_example_config()
        if example:
            shutil.copy(example, cfg_path)
            print(f"✓ wrote starter config → {cfg_path}")
            print("  edit it: set provider.api_key (or env) and your 4 telegram bot tokens.")
        else:
            print("! could not locate config.example.yaml; create the config manually.")
    else:
        print(f"• config already exists → {cfg_path} (left untouched)")

    cfg = Config.load(args.config)
    ws = Workspace(cfg.workspace)
    ws.init()
    (ws.root / ".souls").mkdir(exist_ok=True)
    (ws.root / ".templates").mkdir(exist_ok=True)
    print(f"✓ PARA workspace ready → {ws.root}")
    print("  drop custom SOUL.md overrides in .souls/, custom templates in .templates/")
    return 0


def cmd_run(args) -> int:
    cfg = Config.load(args.config)
    _setup_logging(cfg.behavior.get("log_level", "info"))
    from .providers import build_provider
    from .workspace import Workspace
    from .channels import Gateway

    ws = Workspace(cfg.workspace)
    ws.init()
    gateway = Gateway(cfg, build_provider(cfg.provider), ws)
    try:
        asyncio.run(gateway.run())
    except KeyboardInterrupt:
        print("\nbye.")
    return 0


def cmd_chat(args) -> int:
    if args.agent not in AGENTS:
        print(f"unknown agent {args.agent!r}; choose from {', '.join(AGENTS)}", file=sys.stderr)
        return 2
    cfg = Config.load(args.config)
    ws, _, agents = _build_runtime(cfg)
    ws.init()
    reply = asyncio.run(agents[args.agent].handle(Message(text=args.text, sender="cli")))
    print(reply.rendered())
    return 0


def cmd_capture(args) -> int:
    cfg = Config.load(args.config)
    ws, _, agents = _build_runtime(cfg)
    ws.init()
    reply = asyncio.run(agents["scout"].handle(Message(text=args.text, sender="cli")))
    print(reply.rendered())
    return 0


def cmd_draft(args) -> int:
    cfg = Config.load(args.config)
    ws, _, agents = _build_runtime(cfg)
    ws.init()
    reply = asyncio.run(agents["publisher"].handle(Message(text=args.text, sender="cli")))
    print(reply.rendered())
    return 0


def cmd_scan(args) -> int:
    cfg = Config.load(args.config)
    ws, _, agents = _build_runtime(cfg)
    ws.init()
    reply = asyncio.run(agents["alchemist"].scan_insights())
    print(reply.rendered() if not reply.skip else "(not enough notes yet to find a pattern)")
    return 0


def cmd_map(args) -> int:
    cfg = Config.load(args.config)
    ws, _, agents = _build_runtime(cfg)
    ws.init()
    reply = asyncio.run(agents["librarian"].weekly_map())
    print(reply.rendered())
    return 0


def _find_example_config() -> Path | None:
    # installed alongside the package, or at repo root during development
    for cand in (Path(__file__).resolve().parent.parent / "config.example.yaml",):
        if cand.exists():
            return cand
    try:
        f = resources.files("alchemist").joinpath("../config.example.yaml")
        if f.is_file():  # type: ignore[attr-defined]
            return Path(str(f))
    except Exception:
        pass
    return None


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="alchemist", description="龙虾知识炼金系统")
    p.add_argument("--config", help=f"config path (default {DEFAULT_CONFIG_PATH})")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="create workspace + starter config").set_defaults(fn=cmd_init)
    sub.add_parser("run", help="start the gateway (bots + scheduler)").set_defaults(fn=cmd_run)

    c = sub.add_parser("chat", help="talk to one agent locally")
    c.add_argument("agent", choices=AGENTS)
    c.add_argument("text")
    c.set_defaults(fn=cmd_chat)

    for name, fn, help_ in (
        ("capture", cmd_capture, "scout-capture text from the terminal"),
        ("draft", cmd_draft, "publisher draft from a request"),
    ):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("text")
        sp.set_defaults(fn=fn)

    sub.add_parser("scan", help="run the insight scan once").set_defaults(fn=cmd_scan)
    sub.add_parser("map", help="run the weekly map once").set_defaults(fn=cmd_map)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except (RuntimeError, ValueError, FileNotFoundError) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
