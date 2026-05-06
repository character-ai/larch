#!/usr/bin/env bash
# read-plugin-version.sh — best-effort larch plugin version reader.
#
# Intentionally omits `set -e`: this helper is diagnostic metadata plumbing and
# must always emit a fallback value instead of failing its caller.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || printf '.')"
DEFAULT_PLUGIN_ROOT="$(cd "$SCRIPT_DIR/.." 2>/dev/null && pwd || printf '.')"
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$DEFAULT_PLUGIN_ROOT}"
PLUGIN_JSON="$PLUGIN_ROOT/.claude-plugin/plugin.json"

VERSION="unknown"

if command -v jq >/dev/null 2>&1 && [ -f "$PLUGIN_JSON" ] && [ -r "$PLUGIN_JSON" ]; then
    parsed="$(jq -r '.version // "unknown"' "$PLUGIN_JSON" 2>/dev/null || true)"
    parsed="${parsed%%$'\n'*}"
    parsed="${parsed%%$'\r'*}"
    if [ -n "$parsed" ] && [ "$parsed" != "null" ]; then
        VERSION="$parsed"
    fi
fi

printf 'LARCH_PLUGIN_VERSION=%s\n' "$VERSION"
exit 0
