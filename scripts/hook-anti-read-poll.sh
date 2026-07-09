#!/usr/bin/env bash
# hook-anti-read-poll.sh — PostToolUse hook: warn on repeated identical Read calls.
#
# Generic Read: third consecutive read of the same path+offset within 30s.
# set -e intentionally omitted: hooks must never block tool use.

set -uo pipefail

INPUT=$(cat 2>/dev/null) || exit 0
command -v jq >/dev/null 2>&1 || exit 0

tool_name=$(printf '%s' "$INPUT" | jq -r '.tool_name // ""' 2>/dev/null) || exit 0
[ "$tool_name" = "Read" ] || exit 0

cwd=$(printf '%s' "$INPUT" | jq -r '.cwd // ""' 2>/dev/null) || cwd=""
cwd_hash=$(printf '%s' "${cwd:-/}" | cksum 2>/dev/null | awk '{print $1}') || cwd_hash="0"

session_id=$(printf '%s' "$INPUT" | jq -r '.session_id // ""' 2>/dev/null) || session_id=""
if [ -z "$session_id" ]; then
    session_id=$(printf '%s' "$INPUT" | jq -r '.conversation_id // ""' 2>/dev/null) || session_id=""
fi
if [ -n "$session_id" ]; then
    session_key="$session_id"
elif [ -n "${HOOK_ANTI_READ_POLL_DISCRIMINATOR:-}" ]; then
    session_key="nosession-${HOOK_ANTI_READ_POLL_DISCRIMINATOR}"
else
    session_key="nosession"
fi
session_hash=$(printf '%s' "$session_key" | cksum 2>/dev/null | awk '{print $1}') || session_hash="0"

if [ -n "${HOOK_ANTI_READ_POLL_NOW:-}" ]; then
    now=$HOOK_ANTI_READ_POLL_NOW
    case "$now" in ''|*[!0-9]*) exit 0 ;; esac
else
    now=$(date +%s 2>/dev/null) || exit 0
fi

state_dir="${TMPDIR:-/tmp}/larch-read-poll"
[ -L "$state_dir" ] && exit 0
[ -e "$state_dir" ] && [ ! -d "$state_dir" ] && exit 0
mkdir -p "$state_dir" 2>/dev/null || exit 0
[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || exit 0
chmod 700 "$state_dir" 2>/dev/null || true
[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || exit 0

emit_reminder() {
    local msg="$1"
    jq -cn --arg ctx "$msg"         '{hookSpecificOutput:{hookEventName:"PostToolUse",additionalContext:$ctx}}'         2>/dev/null || true
}

file_path=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null) || exit 0
[ -n "$file_path" ] || exit 0
offset=$(printf '%s' "$INPUT" | jq -r '.tool_input.offset // 0' 2>/dev/null) || offset=0
case "$offset" in ''|*[!0-9-]*) offset=0 ;; esac
path_hash=$(printf '%s' "$file_path" | cksum 2>/dev/null | awk '{print $1}') || path_hash="0"
key="read-${cwd_hash}-${session_hash}"
state_file="$state_dir/$key.state"
prev_path=""; prev_offset=""; prev_count=0; prev_time=0
[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || exit 0
if [ ! -L "$state_file" ] && [ -f "$state_file" ] && [ -r "$state_file" ]; then
    IFS='	' read -r prev_path prev_offset prev_count prev_time <"$state_file" || true
fi
case "$prev_count" in ''|*[!0-9]*) prev_count=0 ;; esac
case "$prev_time" in ''|*[!0-9]*) prev_time=0 ;; esac

if [ "$prev_path" = "$path_hash" ] && [ "$prev_offset" = "$offset" ] && [ $((now - prev_time)) -le 30 ] && [ $((now - prev_time)) -ge 0 ]; then
    count=$((prev_count + 1))
else
    count=1
fi
[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || exit 0
tmp_state=$(mktemp "$state_dir/.${key}.tmp.XXXXXX" 2>/dev/null) || exit 0
[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || { rm -f "$tmp_state" 2>/dev/null || true; exit 0; }
if [ -L "$state_file" ]; then
    rm -f "$state_file" 2>/dev/null || { rm -f "$tmp_state" 2>/dev/null || true; exit 0; }
elif [ -e "$state_file" ] && [ ! -f "$state_file" ]; then
    rm -f "$tmp_state" 2>/dev/null || true
    exit 0
fi
printf '%s	%s	%s	%s
' "$path_hash" "$offset" "$count" "$now" >"$tmp_state" 2>/dev/null || { rm -f "$tmp_state" 2>/dev/null || true; exit 0; }
[ -d "$state_dir" ] && [ ! -L "$state_dir" ] || { rm -f "$tmp_state" 2>/dev/null || true; exit 0; }
if [ -L "$state_file" ]; then
    rm -f "$state_file" 2>/dev/null || { rm -f "$tmp_state" 2>/dev/null || true; exit 0; }
elif [ -e "$state_file" ] && [ ! -f "$state_file" ]; then
    rm -f "$tmp_state" 2>/dev/null || true
    exit 0
fi
mv "$tmp_state" "$state_file" 2>/dev/null || { rm -f "$tmp_state" 2>/dev/null || true; exit 0; }
if [ "$count" -eq 3 ]; then
    emit_reminder "Read-poll detected: repeated identical Read calls. Use one read after state changes instead of polling."
fi
exit 0
