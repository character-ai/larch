#!/usr/bin/env bash
# hook-anti-read-poll.sh — PostToolUse hook: warn on repeated identical Read calls.
#
# Emits a system-reminder on the third consecutive Read of the same path+offset
# within a 30-second window. Different offsets count as distinct reads.
# set -e intentionally omitted: hooks must never block tool use.

set -uo pipefail

INPUT=$(cat 2>/dev/null) || exit 0
command -v jq >/dev/null 2>&1 || exit 0

tool_name=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null) || exit 0
[ "$tool_name" = "Read" ] || exit 0

file_path=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null) || exit 0
[ -n "$file_path" ] || exit 0

offset=$(printf '%s' "$INPUT" | jq -r '.tool_input.offset // 0' 2>/dev/null) || offset=0
case "$offset" in ''|*[!0-9]*) offset=0 ;; esac

cwd=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null) || cwd=""
cwd_hash=$(printf '%s' "${cwd:-/}" | cksum 2>/dev/null | awk '{print $1}') || cwd_hash="0"

POLL_THRESHOLD=3
WINDOW_SECS=30

state_dir="${TMPDIR:-/tmp}/larch-read-poll"
mkdir -p "$state_dir" 2>/dev/null || exit 0
chmod 700 "$state_dir" 2>/dev/null || true
state_file="$state_dir/state-${cwd_hash}.tsv"

if [ -n "${HOOK_ANTI_READ_POLL_NOW:-}" ]; then
    now=$HOOK_ANTI_READ_POLL_NOW
    case "$now" in ''|*[!0-9]*) exit 0 ;; esac
else
    now=$(date +%s 2>/dev/null) || exit 0
fi

last_path="" last_offset="0" count=0 first_ts=0
if [ -f "$state_file" ]; then
    IFS=$'\t' read -r last_path last_offset count first_ts < "$state_file" 2>/dev/null || true
    case "$count" in ''|*[!0-9]*) count=0 ;; esac
    case "$first_ts" in ''|*[!0-9]*) first_ts=0 ;; esac
fi

if [ "$file_path" = "$last_path" ] && [ "$offset" = "$last_offset" ]; then
    age=$(( now - first_ts ))
    if [ "$age" -gt "$WINDOW_SECS" ]; then
        count=1
        first_ts=$now
    else
        count=$((count + 1))
    fi
else
    count=1
    first_ts=$now
fi

printf '%s\t%s\t%s\t%s\n' "$file_path" "$offset" "$count" "$first_ts" > "$state_file" 2>/dev/null || true
chmod 600 "$state_file" 2>/dev/null || true

age=$(( now - first_ts ))
if [ "$count" -eq "$POLL_THRESHOLD" ] && [ "$age" -le "$WINDOW_SECS" ]; then
    msg="[system-reminder] Read-poll detected: the same path+offset has been read $count times consecutively within ${age}s. If waiting for a file to appear, use the Bash background-job completion notification instead of polling with repeated Read calls."
    jq -cn --arg ctx "$msg" \
        '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}' \
        2>/dev/null || true
fi

exit 0
