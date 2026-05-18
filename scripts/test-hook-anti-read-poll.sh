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
out1=$(run_hook 0 "/tmp/file.md" 0 "/proj")
if [ -z "$out1" ]; then pass 'call 1 silent'; else fail "call 1 should be silent, got: $out1"; fi
out2=$(run_hook 1 "/tmp/file.md" 0 "/proj")
if [ -z "$out2" ]; then pass 'call 2 silent'; else fail "call 2 should be silent, got: $out2"; fi

echo "=== third call fires the warning ==="
out3=$(run_hook 2 "/tmp/file.md" 0 "/proj")
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
if printf '%s' "$out3" | grep -q '/tmp/file.md'; then
    fail "warning message should not include raw path: $out3"
else
    pass 'warning message omits raw path'
fi

echo "=== different offset resets counter ==="
# Same cwd, new offset resets the consecutive-read streak.
out_off=$(run_hook 3 "/tmp/file.md" 100 "/proj")
if [ -z "$out_off" ]; then pass 'different offset: call 1 silent'; else fail "different offset call 1 should be silent, got: $out_off"; fi
out_off2=$(run_hook 4 "/tmp/file.md" 100 "/proj")
if [ -z "$out_off2" ]; then pass 'different offset: call 2 silent'; else fail "different offset call 2 should be silent, got: $out_off2"; fi

echo "=== warning fires only on threshold crossing ==="
out4=$(run_hook 5 "/tmp/file.md" 100 "/proj")
if printf '%s' "$out4" | grep -q 'Read-poll detected'; then
    pass 'call 3 at new offset fires warning'
else
    fail "call 3 at new offset should fire warning, got: $out4"
fi
out5=$(run_hook 6 "/tmp/file.md" 100 "/proj")
if [ -z "$out5" ]; then
    pass 'call 4 at new offset stays silent'
else
    fail "call 4 at new offset should be silent, got: $out5"
fi

echo "=== different path resets counter ==="
# Use a fresh cwd to start clean
out_p1=$(run_hook 0 "/tmp/other.md" 0 "/proj2")
if [ -z "$out_p1" ]; then pass 'new path call 1 silent'; else fail "new path call 1 should be silent, got: $out_p1"; fi
out_p2=$(run_hook 1 "/tmp/other.md" 0 "/proj2")
if [ -z "$out_p2" ]; then pass 'new path call 2 silent'; else fail "new path call 2 should be silent, got: $out_p2"; fi
# Switch path — counter resets
out_p3=$(run_hook 2 "/tmp/different.md" 0 "/proj2")
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

echo "=== future timestamp resets skewed state ==="
out_s1=$(run_hook 100 "/tmp/skew.md" 0 "/proj-skew")
if [ -z "$out_s1" ]; then pass 'skew call 1 silent'; else fail "skew call 1 should be silent, got: $out_s1"; fi
out_s2=$(run_hook 101 "/tmp/skew.md" 0 "/proj-skew")
if [ -z "$out_s2" ]; then pass 'skew call 2 silent'; else fail "skew call 2 should be silent, got: $out_s2"; fi
state_skew="$TMP/larch-read-poll/state-$(printf '%s' "/proj-skew" | cksum | awk '{print $1}').tsv"
printf '/tmp/skew.md\t0\t2\t200\n' > "$state_skew"
out_s3=$(run_hook 102 "/tmp/skew.md" 0 "/proj-skew")
if [ -z "$out_s3" ]; then pass 'future timestamp resets skewed state'; else fail "future timestamp should reset state, got: $out_s3"; fi
out_s4=$(run_hook 103 "/tmp/skew.md" 0 "/proj-skew")
if [ -z "$out_s4" ]; then pass 'skew reset call 2 silent'; else fail "skew reset call 2 should be silent, got: $out_s4"; fi
out_s5=$(run_hook 104 "/tmp/skew.md" 0 "/proj-skew")
if printf '%s' "$out_s5" | grep -q 'Read-poll detected'; then
    pass 'skew reset call 3 fires warning'
else
    fail "skew reset call 3 should fire warning, got: $out_s5"
fi

echo "=== tabs and newlines in path do not corrupt state ==="
path_ctrl=$'/tmp/path\twith\ncontrols.md'
out_c1=$(run_hook 0 "$path_ctrl" 0 "/proj-controls")
if [ -z "$out_c1" ]; then pass 'control-char path call 1 silent'; else fail "control-char path call 1 should be silent, got: $out_c1"; fi
out_c2=$(run_hook 1 "$path_ctrl" 0 "/proj-controls")
if [ -z "$out_c2" ]; then pass 'control-char path call 2 silent'; else fail "control-char path call 2 should be silent, got: $out_c2"; fi
out_c3=$(run_hook 2 "$path_ctrl" 0 "/proj-controls")
if printf '%s' "$out_c3" | grep -q 'Read-poll detected'; then
    pass 'control-char path call 3 fires warning'
else
    fail "control-char path call 3 should fire warning, got: $out_c3"
fi
state_controls="$TMP/larch-read-poll/state-$(printf '%s' "/proj-controls" | cksum | awk '{print $1}').tsv"
stored_line=$(cat "$state_controls")
tab_count=$(printf '%s' "$stored_line" | awk -F '\t' '{print NF-1}')
if [ "$tab_count" -eq 3 ]; then
    pass 'control-char path keeps TSV field count stable'
else
    fail "state TSV should keep 4 fields, got line: $stored_line"
fi

echo "=== state file is private ==="
state_file="$TMP/larch-read-poll/state-$(printf '%s' "/proj-window" | cksum | awk '{print $1}').tsv"
# Avoid parsing `stat` output: GNU `-f` is not BSD `-f`, and BSD `%a` is atime (not mode).
if find "$state_file" -perm 600 2>/dev/null | grep -q .; then
    pass 'state file mode is 600'
else
    fail "state file mode should be 600 (find -perm 600 mismatch): $state_file"
fi

[ "$FAIL" -eq 0 ] || exit 1
printf 'All tests passed. PASS=%s\n' "$PASS"
