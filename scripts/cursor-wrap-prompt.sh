#!/usr/bin/env bash
# cursor-wrap-prompt.sh — Wrap a Cursor prompt with the max-mode slash-command prefix.
#
# Emits " /max-mode on. Prompt: <prompt>" (leading space intentional, no trailing
# newline) on stdout. Single source of truth for the max-mode prefix literal.
#
# Cursor supports ~/.cursor/cli-config.json for max-mode and model pinning. Each
# larch invocation uses a private per-invocation config dir (via CURSOR_CONFIG_DIR
# set by cursor_launcher_setup_private_config_dir) seeded from the user's
# cli-config.json to avoid the shared-file rename race under parallel agents.
# Prepending the /max-mode slash command to the prompt is the additional mechanism
# larch controls to request max-mode from its own invocations.
#
# Usage:
#   cursor-wrap-prompt.sh "<prompt>"
#
# Output (stdout):
#   " /max-mode on. Prompt: <prompt>"   (no trailing newline)
#
# Exit codes:
#   0 — success
#   1 — no prompt argument provided

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "cursor-wrap-prompt.sh: a single prompt argument is required" >&2
    exit 1
fi

printf ' /max-mode on. Prompt: %s' "$1"
