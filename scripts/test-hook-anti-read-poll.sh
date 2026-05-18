#!/usr/bin/env bash
# test-hook-anti-read-poll.sh — offline harness for hook-anti-read-poll.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HOOK="$SCRIPT_DIR/hook-anti-read-poll.sh"

[ -x "$HOOK" ] || { echo "FAIL: $HOOK not executable" >&2; exit 1; }

PASS=0; FAIL=0
pass() { PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-hook-anti-read-poll.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

mk_payload() {
    local path="$1" offset="${2:-0}" cwd="${3:-/tmp/test-proj}"
    jq -cn --arg p "$path" --argjson off "$offset" --arg cwd "$cwd" \
        '{tool_name:"Read",tool_input:{file_path:$p,offset:$off},cwd:$cwd}'
}

export TMPDIR="$TMP"

echo "=== first two calls do not fire ==="
out1=$(mk_payload "/tmp/file.md" 0 "/proj" | "$HOOK")
if [ -z "$out1" ]; then pass 'call 1 silent'; else fail "call 1 should be silent, got: $out1"; fi
out2=$(mk_payload "/tmp/file.md" 0 "/proj" | "$HOOK")
if [ -z "$out2" ]; then pass 'call 2 silent'; else fail "call 2 should be silent, got: $out2"; fi

echo "=== third call fires the warning ==="
out3=$(mk_payload "/tmp/file.md" 0 "/proj" | "$HOOK")
if printf '%s' "$out3" | grep -q 'additionalContext'; then
    pass 'call 3 fires warning'
else
    fail "call 3 should fire warning, got: $out3"
fi
if printf '%s' "$out3" | grep -q 'Read-poll detected'; then
    pass 'warning message content present'
else
    fail "warning message content missing: $out3"
fi

echo "=== different offset resets counter ==="
# Wipe state by using a new cwd
out_off=$(mk_payload "/tmp/file.md" 100 "/proj" | "$HOOK")
if [ -z "$out_off" ]; then pass 'different offset: call 1 silent'; else fail "different offset call 1 should be silent, got: $out_off"; fi
out_off2=$(mk_payload "/tmp/file.md" 100 "/proj" | "$HOOK")
if [ -z "$out_off2" ]; then pass 'different offset: call 2 silent'; else fail "different offset call 2 should be silent, got: $out_off2"; fi

echo "=== different path resets counter ==="
# Use a fresh cwd to start clean
out_p1=$(mk_payload "/tmp/other.md" 0 "/proj2" | "$HOOK")
if [ -z "$out_p1" ]; then pass 'new path call 1 silent'; else fail "new path call 1 should be silent, got: $out_p1"; fi
out_p2=$(mk_payload "/tmp/other.md" 0 "/proj2" | "$HOOK")
if [ -z "$out_p2" ]; then pass 'new path call 2 silent'; else fail "new path call 2 should be silent, got: $out_p2"; fi
# Switch path — counter resets
out_p3=$(mk_payload "/tmp/different.md" 0 "/proj2" | "$HOOK")
if [ -z "$out_p3" ]; then pass 'switched path call 1 silent'; else fail "switched path call 1 should be silent, got: $out_p3"; fi

echo "=== non-Read tool is ignored ==="
out_bash=$(jq -cn '{tool_name:"Bash",tool_input:{command:"ls"},cwd:"/proj"}' | "$HOOK")
if [ -z "$out_bash" ]; then pass 'Bash tool ignored'; else fail "Bash tool should be ignored, got: $out_bash"; fi

[ "$FAIL" -eq 0 ] || exit 1
printf 'All tests passed. PASS=%s\n' "$PASS"
