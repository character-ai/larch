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

run_hook() {
    local now="$1" path="$2" offset="${3:-0}" cwd="${4:-/tmp/test-proj}"
    mk_payload "$path" "$offset" "$cwd" | HOOK_ANTI_READ_POLL_NOW="$now" "$HOOK"
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
# Same cwd, new offset resets the consecutive-read streak.
out_off=$(mk_payload "/tmp/file.md" 100 "/proj" | "$HOOK")
if [ -z "$out_off" ]; then pass 'different offset: call 1 silent'; else fail "different offset call 1 should be silent, got: $out_off"; fi
out_off2=$(mk_payload "/tmp/file.md" 100 "/proj" | "$HOOK")
if [ -z "$out_off2" ]; then pass 'different offset: call 2 silent'; else fail "different offset call 2 should be silent, got: $out_off2"; fi

echo "=== fourth identical read still fires ==="
out4=$(mk_payload "/tmp/file.md" 100 "/proj" | "$HOOK")
if printf '%s' "$out4" | grep -q 'Read-poll detected'; then
    pass 'call 4 fires warning again'
else
    fail "call 4 should fire warning, got: $out4"
fi

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

echo "=== expired window resets before recounting ==="
out_w1=$(run_hook 0 "/tmp/window.md" 0 "/proj-window")
if [ -z "$out_w1" ]; then pass 'window call 1 silent'; else fail "window call 1 should be silent, got: $out_w1"; fi
out_w2=$(run_hook 1 "/tmp/window.md" 0 "/proj-window")
if [ -z "$out_w2" ]; then pass 'window call 2 silent'; else fail "window call 2 should be silent, got: $out_w2"; fi
out_w3=$(run_hook 35 "/tmp/window.md" 0 "/proj-window")
if [ -z "$out_w3" ]; then pass 'expired window resets at late call'; else fail "expired window reset call should be silent, got: $out_w3"; fi
out_w4=$(run_hook 36 "/tmp/window.md" 0 "/proj-window")
if [ -z "$out_w4" ]; then pass 'post-reset call 2 silent'; else fail "post-reset call 2 should be silent, got: $out_w4"; fi
out_w5=$(run_hook 37 "/tmp/window.md" 0 "/proj-window")
if printf '%s' "$out_w5" | grep -q 'Read-poll detected'; then
    pass 'post-reset call 3 fires warning'
else
    fail "post-reset call 3 should fire warning, got: $out_w5"
fi

echo "=== state file is private ==="
state_file="$TMP/larch-read-poll/state-$(printf '%s' "/proj-window" | cksum | awk '{print $1}').tsv"
state_mode=$(stat -f '%Mp%Lp' "$state_file" 2>/dev/null || stat -c '%a' "$state_file" 2>/dev/null || true)
if [ "$state_mode" = "600" ] || [ "$state_mode" = "0600" ]; then
    pass 'state file mode is 600'
else
    fail "state file mode should be 600, got: ${state_mode:-missing}"
fi

[ "$FAIL" -eq 0 ] || exit 1
printf 'All tests passed. PASS=%s\n' "$PASS"
