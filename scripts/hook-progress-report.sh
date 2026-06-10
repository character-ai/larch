#!/usr/bin/env bash
# hook-progress-report.sh — UserPromptSubmit hook for typed p/progress reports.
# set -e intentionally omitted: this hook runs on every prompt and must fail open.

set -uo pipefail

INPUT=$(cat 2>/dev/null) || exit 0
command -v jq >/dev/null 2>&1 || exit 0

parsed=$(printf '%s' "$INPUT" | jq -r '
  (.prompt // "" | gsub("^[ \t\r\n]+|[ \t\r\n]+$"; "")) as $prompt
  | if ($prompt == "p" or $prompt == "progress") then
      "MATCH\n" + (.cwd // "")
    else
      empty
    end
' 2>/dev/null) || exit 0
[ -n "$parsed" ] || exit 0
case "$parsed" in
    MATCH$'\n'*) HOOK_CWD=${parsed#*$'\n'} ;;
    MATCH) HOOK_CWD="" ;;
    *) exit 0 ;;
esac

if [ "${HOOK_PROGRESS_TEST_MODE:-}" = "1" ]; then
    [ "${HOOK_PROGRESS_TEST_ERROR:-}" = "1" ] && exit 0
    report=${HOOK_PROGRESS_TEST_OUTPUT:-}
else
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P 2>/dev/null)" || exit 0
    PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd -P 2>/dev/null)}" || exit 0
    [ -n "$PLUGIN_ROOT" ] || exit 0
    report=$(python3 "$PLUGIN_ROOT/python/cli.py" progress report --cwd "$HOOK_CWD" 2>/dev/null) || exit 0
fi

[ -n "$report" ] || exit 0
jq -cn --arg reason "$report" '{decision:"block",reason:$reason}' 2>/dev/null || true
exit 0
