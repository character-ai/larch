#!/usr/bin/env bash
# read-claude-model.sh — best-effort Claude model reader.
#
# Intentionally omits `set -e`: this helper is diagnostic metadata plumbing and
# must always emit a fallback value instead of failing its caller.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || printf '.')"
MODEL="unknown"

if command -v jq >/dev/null 2>&1; then
    source_out="$("$SCRIPT_DIR/token-claude-source.sh" 2>/dev/null || true)"
    transcript=""
    while IFS= read -r line; do
        case "$line" in
            TRANSCRIPT_PATH=*) transcript="${line#TRANSCRIPT_PATH=}" ;;
        esac
    done <<< "$source_out"

    if [ -n "$transcript" ] && [ -f "$transcript" ] && [ -r "$transcript" ]; then
        parsed="$(jq -r 'select(.type=="assistant" and (.message.model? // "") != "") | .message.model' \
            "$transcript" 2>/dev/null | head -n 1 || true)"
        parsed="${parsed%%$'\n'*}"
        parsed="${parsed%%$'\r'*}"
        if [ -n "$parsed" ] && [ "$parsed" != "null" ]; then
            MODEL="$parsed"
        fi
    fi
fi

printf 'CLAUDE_MODEL=%s\n' "$MODEL"
exit 0
