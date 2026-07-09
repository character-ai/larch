#!/usr/bin/env bash
# test-hook-anti-read-poll.sh — offline harness for hook-anti-read-poll.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
HOOK="$SCRIPT_DIR/hook-anti-read-poll.sh"
HOOKS_JSON="$REPO_ROOT/hooks/hooks.json"

[ -x "$HOOK" ] || { echo "FAIL: $HOOK not executable" >&2; exit 1; }
PASS=0; FAIL=0
pass() { PASS=$((PASS+1)); printf 'PASS: %s
' "$1"; }
fail() { FAIL=$((FAIL+1)); printf 'FAIL: %s
' "$1" >&2; }
TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-hook-anti-read-poll.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
export TMPDIR="$TMP"

mk_payload() {
    local path="$1" offset="${2:-0}" cwd="${3:-/tmp/test-proj}" session_id="${4:-}"
    jq -cn --arg p "$path" --argjson off "$offset" --arg cwd "$cwd" --arg sid "$session_id"         '{tool_name:"Read",tool_input:{file_path:$p,offset:$off},cwd:$cwd}
         + (if ($sid|length) > 0 then {session_id:$sid} else {} end)'
}
mk_bash_payload() {
    local command="$1" cwd="${2:-/tmp/test-proj}" session_id="${3:-}"
    jq -cn --arg cmd "$command" --arg cwd "$cwd" --arg sid "$session_id"         '{tool_name:"Bash",tool_input:{command:$cmd},cwd:$cwd}
         + (if ($sid|length) > 0 then {session_id:$sid} else {} end)'
}
run_hook() {
    local now="$1" path="$2" offset="${3:-0}" cwd="${4:-/tmp/test-proj}" session_id="${5:-}"
    mk_payload "$path" "$offset" "$cwd" "$session_id" | HOOK_ANTI_READ_POLL_NOW="$now" "$HOOK"
}
assert_reminder() {
    local out="$1" label="$2"
    if printf '%s' "$out" | command grep -q 'Read-poll detected'; then pass "$label"; else fail "$label (got: $out)"; fi
}
assert_silent() {
    local out="$1" label="$2"
    if [ -z "$out" ]; then pass "$label"; else fail "$label (got: $out)"; fi
}

if jq -e --arg cmd 'hook-anti-read-poll.sh' '.hooks.PostToolUse[]? | select(.matcher == "Read|Bash") | .hooks[]? | select(.command | test($cmd))' "$HOOKS_JSON" >/dev/null 2>&1; then
    pass 'hooks.json registers hook-anti-read-poll.sh under matcher Read|Bash'
else
    fail 'hooks.json must register hook-anti-read-poll.sh under matcher Read|Bash'
fi

assert_silent "$(run_hook 0 /tmp/file.md 0 /proj generic)" 'call 1 silent'
assert_silent "$(run_hook 1 /tmp/file.md 0 /proj generic)" 'call 2 silent'
assert_reminder "$(run_hook 2 /tmp/file.md 0 /proj generic)" 'call 3 warns'
assert_silent "$(run_hook 3 /tmp/file.md 0 /proj generic)" 'call 4 after threshold silent'
assert_silent "$(run_hook 4 /tmp/file.md 100 /proj offset)" 'different offset call 1 silent'
assert_silent "$(run_hook 5 /tmp/file.md 100 /proj offset)" 'different offset call 2 silent'
assert_reminder "$(run_hook 6 /tmp/file.md 100 /proj offset)" 'different offset call 3 warns'
assert_silent "$(run_hook 40 /tmp/file.md 100 /proj slow)" 'slow call 1 silent'
assert_silent "$(run_hook 71 /tmp/file.md 100 /proj slow)" 'window expiry resets counter'
assert_silent "$(mk_bash_payload 'cat tasks/example.output' /proj bash | HOOK_ANTI_READ_POLL_NOW=0 "$HOOK")" 'Bash events ignored'

if [ "$FAIL" -ne 0 ]; then
    printf 'FAIL: test-hook-anti-read-poll.sh (%s failures, %s passes)
' "$FAIL" "$PASS" >&2
    exit 1
fi
printf 'PASS: test-hook-anti-read-poll.sh (%s checks)
' "$PASS"
