#!/usr/bin/env bash
# alchemist installer — sets up a venv, installs the package, and inits the workspace.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${ALCHEMIST_VENV:-$HOME/.alchemist/venv}"

echo "▶ alchemist installer"

command -v python3 >/dev/null 2>&1 || { echo "python3 is required"; exit 1; }
PYV=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
echo "  using python $PYV"

echo "▶ creating venv at $VENV_DIR"
python3 -m venv "$VENV_DIR"
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "▶ installing alchemist"
pip install --quiet --upgrade pip
pip install --quiet "$REPO_DIR"

echo "▶ initializing workspace + config"
alchemist init

cat <<EOF

✓ done.

Next steps:
  1. Edit ~/.alchemist/config.yaml — set provider.api_key (or export OPENROUTER_API_KEY)
     and your four Telegram bot tokens (create them with @BotFather).
  2. Add all four bots to one Telegram group. Disable @scout's privacy mode in BotFather
     (/setprivacy → Disable) so it can capture every message.
  3. Try it locally without Telegram:
       source "$VENV_DIR/bin/activate"
       alchemist capture "https://example.com/some-article"
       alchemist chat alchemist "Distill my recent notes"
  4. Go live:
       alchemist run
EOF
