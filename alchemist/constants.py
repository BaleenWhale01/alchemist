"""Project-wide constants and the canonical agent roster."""

from __future__ import annotations

# CODE stages mapped to agent ids, in pipeline order.
AGENTS = ("scout", "librarian", "alchemist", "publisher")

CODE_STAGE = {
    "scout": "Capture",
    "librarian": "Organize",
    "alchemist": "Distill",
    "publisher": "Express",
}

# PARA top-level directories (created on `alchemist init`).
PARA_DIRS = ("Projects", "Areas", "Resources", "Archives")

# Separator appended by alchemist when writing distillation into a note.
DISTILL_MARKER = "--- Distilled ---"

# Message prefixes so a single group chat stays visually scannable (PRD §appendix A).
PREFIX = {
    "weekly_map": "[Weekly Map]",
    "insight": "[Insight]",
    "draft": "[Draft]",
    "capture": "[Captured]",
}

# Default config search path.
DEFAULT_CONFIG_PATH = "~/.alchemist/config.yaml"
DEFAULT_WORKSPACE = "~/.alchemist/workspace"
