#!/usr/bin/env bash
# test-hook-anti-read-poll.sh — offline harness for hook-anti-read-poll.sh.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
HOOK="$SCRIPT_DIR/hook-anti-read-poll.sh"
HOOKS_JSON="$REPO_ROOT/hooks/hooks.json"

[ -x "$HOOK" ] || { echo "FAIL: $HOOK not executable" >&2; exit 1; }

PASS=0; FAIL=0
pass() { PASS=$((PASS+1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL+1)); printf 'FAIL: %s\n' "$1" >&2; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-hook-anti-read-poll.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

mk_payload() {
    local path="$1" offset="${2:-0}" cwd="${3:-/tmp/test-proj}" session_id="${4:-}"
    jq -cn --arg p "$path" --argjson off "$offset" --arg cwd "$cwd" --arg sid "$session_id" \
        '{tool_name:"Read",tool_input:{file_path:$p,offset:$off},cwd:$cwd}
         + (if ($sid|length) > 0 then {session_id:$sid} else {} end)'
}

mk_bash_payload() {
    local command="$1" cwd="${2:-/tmp/test-proj}" session_id="${3:-}"
    jq -cn --arg cmd "$command" --arg cwd "$cwd" --arg sid "$session_id" \
        '{tool_name:"Bash",tool_input:{command:$cmd},cwd:$cwd}
         + (if ($sid|length) > 0 then {session_id:$sid} else {} end)'
}

run_hook() {
    local now="$1" path="$2" offset="${3:-0}" cwd="${4:-/tmp/test-proj}" session_id="${5:-}"
    mk_payload "$path" "$offset" "$cwd" "$session_id" | HOOK_ANTI_READ_POLL_NOW="$now" "$HOOK"
}

run_bash_hook() {
    local now="$1" command="$2" cwd="${3:-/tmp/test-proj}" session_id="${4:-}"
    mk_bash_payload "$command" "$cwd" "$session_id" | HOOK_ANTI_READ_POLL_NOW="$now" "$HOOK"
}

assert_reminder() {
    local out="$1" label="$2"
    if printf '%s' "$out" | grep -q 'additionalContext'; then
        pass "$label"
    else
        fail "$label (expected reminder, got: $out)"
    fi
}

assert_silent() {
    local out="$1" label="$2"
    if [ -z "$out" ]; then
        pass "$label"
    else
        fail "$label (expected silent, got: $out)"
    fi
}

TASK_OUT='/tmp/proj/tasks/testtask123.output'

export TMPDIR="$TMP"

echo "=== hooks.json pins Read|Bash matcher on anti-read-poll hook ==="
if jq -e --arg cmd 'hook-anti-read-poll.sh' '
    .hooks.PostToolUse[]?
    | select(.matcher == "Read|Bash")
    | .hooks[]?
    | select(.command | test($cmd))
' "$HOOKS_JSON" >/dev/null 2>&1; then
    pass 'hooks.json co-locates hook-anti-read-poll.sh with matcher Read|Bash'
else
    fail "hooks.json must register hook-anti-read-poll.sh under matcher Read|Bash in one PostToolUse block"
fi

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

echo "=== non-poll Bash is ignored ==="
out_bash=$(run_bash_hook 0 "ls" "/proj-nonpoll")
assert_silent "$out_bash" 'non-poll Bash (ls) silent'

echo "=== Bash task-output poll fires (#3195) ==="
out_bt1=$(run_bash_hook 0 "cat $TASK_OUT" "/proj-bash-poll")
assert_silent "$out_bt1" 'Bash task-output call 1 silent'
out_bt2=$(run_bash_hook 1 "cat $TASK_OUT" "/proj-bash-poll")
assert_reminder "$out_bt2" 'Bash task-output call 2 fires reminder'

echo "=== multiline Bash task-output poll fires ==="
multiline_cmd=$'export FOO=bar\nVAR=1\ncat '"$TASK_OUT"
out_bm1=$(run_bash_hook 0 "$multiline_cmd" "/proj-bash-multiline")
assert_silent "$out_bm1" 'multiline Bash task-output call 1 silent'
out_bm2=$(run_bash_hook 1 "$multiline_cmd" "/proj-bash-multiline")
assert_reminder "$out_bm2" 'multiline Bash task-output call 2 fires reminder'

echo "=== Bash task-output poll with transcript suffixes ==="
suffix_cmd="cat $TASK_OUT 2>/dev/null | head -5"
out_bs1=$(run_bash_hook 0 "$suffix_cmd" "/proj-bash-suffix")
assert_silent "$out_bs1" 'suffix Bash task-output call 1 silent'
out_bs2=$(run_bash_hook 1 "$suffix_cmd" "/proj-bash-suffix")
assert_reminder "$out_bs2" 'suffix Bash task-output call 2 fires reminder'

echo "=== wrapper-variant Bash polls share one counter ==="
out_bw1=$(run_bash_hook 0 "cat $TASK_OUT" "/proj-bash-wrapper")
assert_silent "$out_bw1" 'wrapper Bash call 1 silent'
out_bw2=$(run_bash_hook 2 "sleep 1 && cat $TASK_OUT 2>/dev/null" "/proj-bash-wrapper")
assert_reminder "$out_bw2" 'wrapper Bash call 2 (variant command) fires reminder'

echo "=== slow Read task-output polling fires ==="
out_sr1=$(run_hook 0 "$TASK_OUT" 0 "/proj-slow-read")
assert_silent "$out_sr1" 'slow Read task-output call 1 silent'
out_sr2=$(run_hook 40 "$TASK_OUT" 0 "/proj-slow-read")
assert_reminder "$out_sr2" 'slow Read task-output call 2 (>30s) fires reminder'

echo "=== offset-ignore for task-output Read ==="
out_of1=$(run_hook 0 "$TASK_OUT" 0 "/proj-task-offset")
assert_silent "$out_of1" 'task-output Read offset call 1 silent'
out_of2=$(run_hook 1 "$TASK_OUT" 50 "/proj-task-offset")
assert_reminder "$out_of2" 'task-output Read offset call 2 fires reminder'

echo "=== false-positive guard: cat notes.txt ==="
out_fp1=$(run_bash_hook 0 "cat notes.txt" "/proj-fp")
assert_silent "$out_fp1" 'cat notes.txt call 1 silent'
out_fp2=$(run_bash_hook 1 "cat notes.txt" "/proj-fp")
assert_silent "$out_fp2" 'cat notes.txt call 2 silent'

echo "=== Read then Bash share task-output counter ==="
REL_TASK_OUT='tasks/crossread123.output'
ABS_TASK_OUT="/tmp/proj/$REL_TASK_OUT"
out_rb1=$(run_hook 0 "$ABS_TASK_OUT" 0 "/proj-read-bash-share")
assert_silent "$out_rb1" 'Read then Bash call 1 silent'
out_rb2=$(run_bash_hook 1 "cat $REL_TASK_OUT" "/proj-read-bash-share")
assert_reminder "$out_rb2" 'Read then Bash call 2 fires reminder'

echo "=== absolute then relative Bash paths share counter ==="
out_mx1=$(run_bash_hook 0 "cat $TASK_OUT" "/proj-mixed-path")
assert_silent "$out_mx1" 'mixed path Bash call 1 silent'
out_mx2=$(run_bash_hook 1 "cat tasks/testtask123.output" "/proj-mixed-path")
assert_reminder "$out_mx2" 'mixed path Bash call 2 fires reminder'

echo "=== relative Read prefix normalizes to tasks tail ==="
REL_PREFIX_OUT='foo/bar/tasks/prefixnorm.output'
out_pn1=$(run_hook 0 "$REL_PREFIX_OUT" 0 "/proj-prefix-norm")
assert_silent "$out_pn1" 'prefix Read call 1 silent'
out_pn2=$(run_bash_hook 1 "cat /tmp/proj/foo/bar/tasks/prefixnorm.output" "/proj-prefix-norm")
assert_reminder "$out_pn2" 'prefix Read then absolute Bash call 2 fires reminder'

echo "=== task-output window expires after 600s ==="
out_te1=$(run_hook 0 "$TASK_OUT" 0 "/proj-task-expiry")
assert_silent "$out_te1" 'task-output expiry call 1 silent'
out_te2=$(run_hook 601 "$TASK_OUT" 0 "/proj-task-expiry")
assert_silent "$out_te2" 'task-output expiry call 2 after 600s silent'
out_te3=$(run_hook 602 "$TASK_OUT" 0 "/proj-task-expiry")
assert_reminder "$out_te3" 'task-output expiry call 3 fires reminder'

echo "=== quoted Bash task-output path polls fire ==="
quoted_cmd="cat '/tmp/proj/tasks/testtask123.output'"
out_q1=$(run_bash_hook 0 "$quoted_cmd" "/proj-quoted-path")
assert_silent "$out_q1" 'quoted Bash task-output call 1 silent'
out_q2=$(run_bash_hook 1 "$quoted_cmd" "/proj-quoted-path")
assert_reminder "$out_q2" 'quoted Bash task-output call 2 fires reminder'

echo "=== echo then cat on same line counts ==="
echo_cat_cmd="echo '=== status ==='; cat $TASK_OUT"
out_ec1=$(run_bash_hook 0 "$echo_cat_cmd" "/proj-echo-cat-line")
assert_silent "$out_ec1" 'echo+cat same line call 1 silent'
out_ec2=$(run_bash_hook 1 "$echo_cat_cmd" "/proj-echo-cat-line")
assert_reminder "$out_ec2" 'echo+cat same line call 2 fires reminder'

echo "=== multiline Bash with two task ids uses matching line token ==="
two_id_ml_cmd=$'cat /tmp/proj/tasks/taskA.output\ncat /tmp/proj/tasks/taskB.output'
out_2id1=$(run_bash_hook 0 "$two_id_ml_cmd" "/proj-two-id-multiline")
assert_silent "$out_2id1" 'two-id multiline call 1 silent'
out_2id2=$(run_bash_hook 1 "$two_id_ml_cmd" "/proj-two-id-multiline")
assert_reminder "$out_2id2" 'two-id multiline call 2 fires reminder for task A'

echo "=== distinct session_id buckets do not share counters ==="
out_s1=$(run_bash_hook 0 "cat $TASK_OUT" "/proj-session-iso" "session-alpha")
assert_silent "$out_s1" 'session alpha call 1 silent'
out_s2=$(run_bash_hook 1 "cat $TASK_OUT" "/proj-session-iso" "session-beta")
assert_silent "$out_s2" 'session beta call 1 silent'
out_s3=$(run_bash_hook 2 "cat $TASK_OUT" "/proj-session-iso" "session-alpha")
assert_reminder "$out_s3" 'session alpha call 2 fires reminder'

echo "=== echo mentioning task path does not count ==="
out_en1=$(run_bash_hook 0 "echo cat $TASK_OUT" "/proj-echo-fp")
assert_silent "$out_en1" 'echo task path call 1 silent'
out_en2=$(run_bash_hook 1 "echo cat $TASK_OUT" "/proj-echo-fp")
assert_silent "$out_en2" 'echo task path call 2 silent'

echo "=== assignment line then unrelated cat is ignored ==="
assign_cmd=$'OUT=tasks/decoy123.output\ncat notes.txt'
out_as1=$(run_bash_hook 0 "$assign_cmd" "/proj-assign-fp")
assert_silent "$out_as1" 'assignment decoy call 1 silent'
out_as2=$(run_bash_hook 1 "$assign_cmd" "/proj-assign-fp")
assert_silent "$out_as2" 'assignment decoy call 2 silent'

echo "=== grep -rn with sed does not false-positive ==="
out_sed1=$(run_bash_hook 0 "sed -i.bak 's/a/b/' notes.txt; grep -rn pattern ." "/proj-sed-fp")
assert_silent "$out_sed1" 'sed edit plus grep -rn call 1 silent'
out_sed2=$(run_bash_hook 1 "sed -i.bak 's/a/b/' notes.txt; grep -rn pattern ." "/proj-sed-fp")
assert_silent "$out_sed2" 'sed edit plus grep -rn call 2 silent'

echo "=== two task ids tracked independently ==="
TASK_A='/tmp/proj/tasks/taskA.output'
TASK_B='/tmp/proj/tasks/taskB.output'
out_ab1=$(run_bash_hook 0 "cat $TASK_A" "/proj-two-tasks")
assert_silent "$out_ab1" 'two tasks A call 1 silent'
out_ab2=$(run_bash_hook 1 "cat $TASK_B" "/proj-two-tasks")
assert_silent "$out_ab2" 'two tasks B call 1 silent'
out_ab3=$(run_bash_hook 2 "cat $TASK_A" "/proj-two-tasks")
assert_reminder "$out_ab3" 'two tasks A call 2 fires reminder'

echo "=== generic Read regression (3 within 30s, 2 do not) ==="
out_gr1=$(run_hook 0 "/tmp/generic-regression.md" 0 "/proj-generic-reg")
assert_silent "$out_gr1" 'generic Read call 1 silent'
out_gr2=$(run_hook 1 "/tmp/generic-regression.md" 0 "/proj-generic-reg")
assert_silent "$out_gr2" 'generic Read call 2 silent'
out_gr3=$(run_hook 2 "/tmp/generic-regression.md" 0 "/proj-generic-reg")
assert_reminder "$out_gr3" 'generic Read call 3 fires reminder'

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
