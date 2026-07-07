#!/usr/bin/env bash
# test-hook-bg-poll-guard.sh — offline harness for hook-bg-poll-guard.sh.
# shellcheck disable=SC2016 # candidate Bash command literals intentionally preserve $DESIGN_TMPDIR.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd -P)"
HOOK="$SCRIPT_DIR/hook-bg-poll-guard.sh"
HOOKS_JSON="$REPO_ROOT/hooks/hooks.json"

[ -x "$HOOK" ] || { echo "FAIL: $HOOK not executable" >&2; exit 1; }

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-hook-bg-poll-guard.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
export TMPDIR="$TMP"
export HOME="$TMP/home"
mkdir -p "$HOME"

D="$TMP/claude-design-bg-guard"
mkdir -p "$D/tasks" "$D/plan-review/round-1"
MARKER="$D/.bg-wait-active"
EXPECTED_STEP="design-step3-review"

write_marker() {
  local pid="$1" start="$2" timeout="${3:-21600}" step="${4:-design-step3-review}"
  EXPECTED_STEP="$step"
  cat >"$MARKER" <<EOF_MARKER
PID=$pid
  CLAUDE_PID=$$
START_EPOCH=$start
STEP=$step
TIMEOUT_S=$timeout
EOF_MARKER
}

payload_read() {
  local path="$1" cwd="${2:-$D}"
  jq -cn --arg p "$path" --arg cwd "$cwd" '{tool_name:"Read",tool_input:{file_path:$p},cwd:$cwd}'
}

payload_bash() {
  local command="$1" cwd="${2:-$D}"
  jq -cn --arg cmd "$command" --arg cwd "$cwd" '{tool_name:"Bash",tool_input:{command:$cmd},cwd:$cwd}'
}

payload_monitor() {
  local cwd="${1:-$D}"
  jq -cn --arg cwd "$cwd" '{tool_name:"Monitor",tool_input:{},cwd:$cwd}'
}

payload_taskoutput() {
  local cwd="${1:-$D}"
  jq -cn --arg cwd "$cwd" '{tool_name:"TaskOutput",tool_input:{},cwd:$cwd}'
}

run_payload() {
  local payload="$1"
  printf '%s' "$payload" | LARCH_BG_POLL_GUARD_MARKER="$MARKER" LARCH_BG_POLL_GUARD_SESSION_PID="${LARCH_BG_POLL_GUARD_SESSION_PID:-}" "$HOOK"
}

run_payload_auto_markers() {
  local payload="$1"
  printf '%s' "$payload" | LARCH_BG_POLL_GUARD_SESSION_PID="${LARCH_BG_POLL_GUARD_SESSION_PID:-$$}" "$HOOK"
}

run_payload_with_marker() {
  local marker="$1" payload="$2"
  printf '%s' "$payload" | LARCH_BG_POLL_GUARD_MARKER="$marker" LARCH_BG_POLL_GUARD_SESSION_PID="${LARCH_BG_POLL_GUARD_SESSION_PID:-}" "$HOOK"
}

write_marker_at() {
  local marker="$1" pid="$2" start="$3" timeout="${4:-21600}" step="${5:-design-step3-review}"
  EXPECTED_STEP="$step"
  cat >"$marker" <<EOF_MARKER
PID=$pid
CLAUDE_PID=$$
START_EPOCH=$start
STEP=$step
TIMEOUT_S=$timeout
EOF_MARKER
}

write_keepalive() {
  local dir="$1" clone_path="$2"
  printf 'CLONE_PATH=%s\n' "$clone_path" >"$dir/.larch-keepalive"
}

assert_allow() {
  local out="$1" label="$2"
  if [ -z "$out" ]; then
    pass "$label"
  else
    fail "$label (expected allow, got: $out)"
  fi
}

assert_deny() {
  local out="$1" label="$2" expected_step="$3" reason actual_step
  if printf '%s' "$out" | jq -e '.hookSpecificOutput.hookEventName == "PreToolUse" and .hookSpecificOutput.permissionDecision == "deny"' >/dev/null 2>&1; then
    pass "$label"
  else
    fail "$label (expected deny JSON, got: $out)"
    return
  fi
  reason=$(printf '%s' "$out" | jq -r '.hookSpecificOutput.permissionDecisionReason // ""' 2>/dev/null || printf '')
  case "$reason" in
    *.bg-wait-active*) ;;
    *) fail "$label deny reason must include the triggering .bg-wait-active marker" ;;
  esac
  actual_step=$(printf '%s' "$reason" | sed -n 's/.*STEP=\([^[:space:]]*\).*/\1/p')
  if [ "$actual_step" != "$expected_step" ]; then
    fail "$label deny reason STEP mismatch: got '$actual_step', want '$expected_step'"
  fi
  case "$reason" in
    *hook_version=*) ;;
    *) fail "$label deny reason must include hook_version metadata" ;;
  esac
}

reset_probe_counters() {
  rm -f "$D"/bg-poll-guard-probe-denials.*.count 2>/dev/null || true
}

if jq -e --arg cmd 'hook-bg-poll-guard.sh' '
    .hooks.PreToolUse[]?
    | select(.matcher == "Read|Bash|Monitor|TaskOutput")
    | .hooks[]?
    | select(.command | test($cmd))
' "$HOOKS_JSON" >/dev/null 2>&1; then
  pass 'hooks.json registers hook-bg-poll-guard.sh under PreToolUse Read|Bash|Monitor|TaskOutput'
else
  fail 'hooks.json must register hook-bg-poll-guard.sh under PreToolUse Read|Bash|Monitor|TaskOutput'
fi

rm -f "$MARKER"
design_tmpdir_ls="ls \"\$DESIGN_TMPDIR\""
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'no marker allows Bash probe'

write_marker 999999 1 1
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'stale marker with dead PID allows'

write_marker $$ "$(date +%s)"
out=$(LARCH_BG_POLL_GUARD_DISABLE=1 run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'disable env var allows'

touch "$D/plan-review/round-1/ballot.txt"
out=$(LARCH_CLAUDE_SUBPROCESS_HOOK_EXEMPT=0 run_payload "$(payload_read "$D/plan-review/round-1/ballot.txt")")
assert_deny "$out" 'live marker plus non-1 Claude subprocess exemption still denies Read' "$EXPECTED_STEP"

out=$(LARCH_CLAUDE_SUBPROCESS_HOOK_EXEMPT=1 run_payload "$(payload_read "$D/plan-review/round-1/ballot.txt")")
assert_allow "$out" 'live marker plus Claude subprocess exemption allows Read'

out=$(LARCH_CLAUDE_SUBPROCESS_HOOK_EXEMPT=1 run_payload "$(payload_monitor)")
assert_allow "$out" 'live marker plus Claude subprocess exemption allows Monitor'

out=$(run_payload "$(payload_read "$D/plan-review/round-1/ballot.txt")")
assert_deny "$out" 'live marker plus Read under DESIGN_TMPDIR denies' "$EXPECTED_STEP"

out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'live marker plus Bash ls DESIGN_TMPDIR denies' "$EXPECTED_STEP"

bgjob_wait_cmd="python3 \"$REPO_ROOT/python/cli.py\" bgjob wait --step design-step3-review --tmpdir \"\$TMPDIR\" --max-wait-s 270"
out=$(run_payload "$(payload_bash "$bgjob_wait_cmd" "$D")")
assert_allow "$out" 'live legacy marker plus bgjob wait command allows'

bgjob_wait_with_probe="$bgjob_wait_cmd && cat \"$D/.step3-review-result.env\""
out=$(run_payload "$(payload_bash "$bgjob_wait_with_probe" "$D")")
assert_deny "$out" 'live legacy marker plus bgjob wait with appended probe denies' "$EXPECTED_STEP"

session_tmpdir_ls="ls \"\$SESSION_TMPDIR\""
out=$(run_payload "$(payload_bash "$session_tmpdir_ls")")
assert_deny "$out" 'live marker plus Bash ls SESSION_TMPDIR denies' "$EXPECTED_STEP"

out=$(run_payload "$(payload_bash 'cat .step3-review-result.env' "$D")")
assert_deny "$out" 'live marker plus cat result env in tmpdir context denies' "$EXPECTED_STEP"

out=$(run_payload "$(payload_bash "sleep 30 && $design_tmpdir_ls")")
assert_deny "$out" 'live marker plus sleep N && probe denies' "$EXPECTED_STEP"

watcher_cmd="while [ ! -f .step3-review-result.env ]; do sleep 5; $design_tmpdir_ls; done"
out=$(run_payload "$(payload_bash "$watcher_cmd")")
assert_deny "$out" 'live marker plus watcher loop denies' "$EXPECTED_STEP"

out=$(run_payload "$(payload_read 'tasks/foo.output' "$REPO_ROOT")")
assert_allow "$out" 'live marker plus Read tasks/foo.output allows classification'

TASK_STORE="$TMP/task-store"
mkdir -p "$TASK_STORE/tasks"
TASK_OUT="$TASK_STORE/tasks/foo.output"
printf '   \n' >"$TASK_OUT"
rm -f "$D"/bg-poll-guard-task-output-read.*.count
write_marker $$ "$(date +%s)" 21600 design-step3-review
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_allow "$out" 'task-output classification clamp allows first whitespace-only Read'
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_allow "$out" 'task-output classification clamp allows second unchanged whitespace-only Read'
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_deny "$out" 'task-output classification clamp denies third unchanged whitespace-only Read' "$EXPECTED_STEP"
if [ -f "$D/no-progress-task-output-clamped" ] && [ -f "$D/no-progress-circuit-breaker-armed" ]; then
  pass 'task-output classification clamp arms no-progress Stop bridge'
else
  fail 'task-output classification clamp must arm no-progress Stop bridge'
fi
printf 'new reviewer output\n' >"$TASK_OUT"
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_allow "$out" 'task-output classification clamp resets on changed non-whitespace content'
if [ ! -f "$D/no-progress-task-output-clamped" ] && [ ! -f "$D/no-progress-circuit-breaker-armed" ]; then
  pass 'changed task-output clears no-progress Stop bridge'
else
  fail 'changed task-output must clear no-progress Stop bridge'
fi
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_allow "$out" 'task-output classification clamp allows second identical non-whitespace Read'
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_deny "$out" 'task-output classification clamp denies third identical non-whitespace Read' "$EXPECTED_STEP"
mkdir -p "$D/.completed"
touch "$D/.completed/step-3-terminal" "$D/.step3-terminal-persisted-this-run"
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_allow "$out" 'terminal sentinel release allows task-output Read'
if ! compgen -G "$D/bg-poll-guard-task-output-read.*.count" >/dev/null && [ ! -f "$D/no-progress-task-output-clamped" ]; then
  pass 'terminal sentinel release clears task-output Read clamp sidecars'
else
  fail 'terminal sentinel release must clear task-output Read clamp sidecars'
fi
rm -f "$D/.completed/step-3-terminal" "$D/.step3-terminal-persisted-this-run"

rm -f "$D"/bg-poll-guard-task-output-read.*.count
printf '   \n' >"$TASK_OUT"
write_marker 999999 "$(date +%s)" 21600 design-step3-review
printf 'whitespace\t1\t1\t3\n' >"$D/bg-poll-guard-task-output-read.foo.count"
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_allow "$out" 'dead PID marker allows task-output Read'
if ! compgen -G "$D/bg-poll-guard-task-output-read.*.count" >/dev/null; then
  pass 'dead PID marker clears task-output Read clamp sidecar'
else
  fail 'dead PID marker must clear task-output Read clamp sidecar'
fi

rm -f "$D"/bg-poll-guard-task-output-read.*.count
write_marker $$ 1 1 design-step3-review
printf 'whitespace\t1\t1\t3\n' >"$D/bg-poll-guard-task-output-read.foo.count"
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_allow "$out" 'aged marker allows task-output Read'
if ! compgen -G "$D/bg-poll-guard-task-output-read.*.count" >/dev/null; then
  pass 'aged marker clears task-output Read clamp sidecar'
else
  fail 'aged marker must clear task-output Read clamp sidecar'
fi

rm -f "$D"/bg-poll-guard-task-output-read.*.count
rm -f "$D/no-progress-task-output-clamped" "$D/no-progress-circuit-breaker-armed"
write_marker $$ "$(date +%s)" 21600 implement-step3-checks
EXPECTED_STEP="implement-step3-checks"
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_allow "$out" 'implement-step task-output classification clamp allows first Read'
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_allow "$out" 'implement-step task-output classification clamp allows second unchanged Read'
out=$(run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_deny "$out" 'implement-step task-output classification clamp denies third unchanged Read' "$EXPECTED_STEP"
if compgen -G "$D/bg-poll-guard-task-output-read.*.count" >/dev/null && [ -f "$D/no-progress-task-output-clamped" ] && [ -f "$D/no-progress-circuit-breaker-armed" ]; then
  pass 'implement-step task-output classification clamp arms no-progress bridge'
else
  fail 'implement-step task-output classification clamp must write telemetry and arm no-progress bridge'
fi
rm -f "$D"/bg-poll-guard-task-output-read.*.count "$D/no-progress-task-output-clamped" "$D/no-progress-circuit-breaker-armed"
write_marker $$ "$(date +%s)" 21600 design-step3-review
EXPECTED_STEP="design-step3-review"

D_FOREIGN="$TMP/claude-design-foreign-task-output"
mkdir -p "$D_FOREIGN"
MARKER_FOREIGN="$D_FOREIGN/.bg-wait-active"
CLONE_OWNER="$TMP/clone-owner"
CLONE_OTHER="$TMP/clone-other"
mkdir -p "$CLONE_OWNER" "$CLONE_OTHER"
write_marker_at "$MARKER_FOREIGN" $$ "$(date +%s)" 21600 design-step3-review
printf 'CLONE_PATH=%s\n' "$CLONE_OWNER" >"$D_FOREIGN/.larch-keepalive"
rm -f "$D_FOREIGN"/bg-poll-guard-task-output-read.*.count
out=$(run_payload_with_marker "$MARKER_FOREIGN" "$(payload_read "$TASK_OUT" "$CLONE_OTHER")")
assert_allow "$out" 'foreign design marker allows task-output Read without clamp'
out=$(run_payload_with_marker "$MARKER_FOREIGN" "$(payload_read "$TASK_OUT" "$CLONE_OTHER")")
assert_allow "$out" 'foreign design marker allows repeated task-output Read without clamp'
out=$(run_payload_with_marker "$MARKER_FOREIGN" "$(payload_read "$TASK_OUT" "$CLONE_OTHER")")
assert_allow "$out" 'foreign design marker does not deny repeated task-output Read'
if ! compgen -G "$D_FOREIGN/bg-poll-guard-task-output-read.*.count" >/dev/null; then
  pass 'foreign design marker does not receive task-output Read clamp telemetry'
else
  fail 'foreign design marker must not receive task-output Read clamp telemetry'
fi

rm -f "$D"/bg-poll-guard-task-output-read.*.count
out=$(LARCH_BG_POLL_GUARD_TASK_OUTPUT_READ_THRESHOLD=1 run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_allow "$out" 'task-output classification threshold override allows first Read'
out=$(LARCH_BG_POLL_GUARD_TASK_OUTPUT_READ_THRESHOLD=1 run_payload "$(payload_read "$TASK_OUT" "$TASK_STORE")")
assert_deny "$out" 'task-output classification threshold override denies second Read' "$EXPECTED_STEP"

rm -f "$D"/bg-poll-guard-task-output-read.*.count
printf 'whitespace\t1\t1\t3\n' >"$D/bg-poll-guard-task-output-read.foo.count"
PYTHONPATH="$REPO_ROOT/python" python3 - "$D" <<'PY'
import sys
from pathlib import Path
from larch.design.design_core import _bg_wait_marker_context

with _bg_wait_marker_context(design_tmpdir=Path(sys.argv[1]), step="design-step3-review"):
    pass
PY
if ! compgen -G "$D/bg-poll-guard-task-output-read.*.count" >/dev/null; then
  pass 'Python design marker arm clears stale task-output Read clamp sidecar'
else
  fail 'Python design marker arm must clear stale task-output Read clamp sidecar'
fi
write_marker $$ "$(date +%s)" 21600 design-step3-review

out=$(run_payload "$(payload_bash "\"\$HOME/.cache/larch/sessions/design-run-123.sh\" design-step3-review.sh")")
assert_allow "$out" 'wrapper-routed design-run call allows'

compound_wrapper_probe="\"\$HOME/.cache/larch/sessions/design-run-123.sh\" design-step3-review.sh && $design_tmpdir_ls"
out=$(run_payload "$(payload_bash "$compound_wrapper_probe")")
assert_deny "$out" 'compound wrapper plus appended probe denies' "$EXPECTED_STEP"

# #4725: the bare background sleep-loop Step 3 recovery waiter is now DENIED (it
# used to be allowed). It is a zero-output background task that breeds its own
# premature notifications, so the guard forces the foreground, non-sleeping
# terminal-sentinel probe path instead.
step3_recovery_waiter="until [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter" "$D")")
assert_deny "$out" 'exact Step 3 recovery waiter denies' "$EXPECTED_STEP"

step3_recovery_waiter_braced="until [ -f \"\${DESIGN_TMPDIR}/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_braced" "$D")")
assert_deny "$out" 'braced Step 3 recovery waiter denies' "$EXPECTED_STEP"

# #4489 / #4725: a single leading DESIGN_TMPDIR=<abs>; assignment still matches the
# exact-waiter shape, so the prefixed waiter is denied too.
step3_recovery_waiter_prefixed="DESIGN_TMPDIR=/tmp/larch-design-xyz; until [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_prefixed" "$D")")
assert_deny "$out" 'DESIGN_TMPDIR-prefixed Step 3 recovery waiter denies' "$EXPECTED_STEP"

step3_recovery_waiter_prefixed_braced="DESIGN_TMPDIR=/tmp/larch-design-xyz; until [ -f \"\${DESIGN_TMPDIR}/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_prefixed_braced" "$D")")
assert_deny "$out" 'DESIGN_TMPDIR-prefixed braced Step 3 recovery waiter denies' "$EXPECTED_STEP"

# #4725: the sanctioned replacement for the denied waiter is the foreground,
# non-sleeping terminal-sentinel probe, which stays allowed when the sentinel is
# absent (WAIT branch). Co-located here to pin the deny-the-loop / allow-the-probe
# contract at the flip site.
write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
reset_probe_counters
step3_foreground_probe_alt="[ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ] && echo DONE || echo WAIT"
out=$(run_payload "$(payload_bash "$step3_foreground_probe_alt" "$D")")
assert_allow "$out" 'foreground terminal-sentinel probe (sanctioned waiter replacement) allows'

step3_recovery_waiter_prefixed_probe="DESIGN_TMPDIR=/tmp/larch-design-xyz; until [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ]; do sleep 30; done && cat \"\$DESIGN_TMPDIR/.step3-review-result.env\""
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_prefixed_probe" "$D")")
assert_deny "$out" 'DESIGN_TMPDIR-prefixed Step 3 recovery waiter with appended probe denies' "$EXPECTED_STEP"

step3_recovery_waiter_probe="until [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ]; do sleep 30; done && cat \"\$DESIGN_TMPDIR/.step3-review-result.env\""
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_probe" "$D")")
assert_deny "$out" 'Step 3 recovery waiter with appended probe denies' "$EXPECTED_STEP"

filetest_loop='while [ ! -f .step3-review-result.env ]; do sleep 5; done'
out=$(run_payload "$(payload_bash "$filetest_loop" "$D")")
assert_deny "$out" 'live marker plus file-test sleep loop denies' "$EXPECTED_STEP"

step3_result_waiter="until [ -f \"\$DESIGN_TMPDIR/.step3-review-result.env\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_result_waiter" "$D")")
assert_deny "$out" 'Step 3 result-env waiter remains denied' "$EXPECTED_STEP"

write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
reset_probe_counters
terminal_probe_step3='[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$terminal_probe_step3" "$D")")
assert_allow "$out" 'absent Step 3 terminal sentinel foreground probe allows'

write_marker $$ "$(date +%s)" 21600 design-step5c
rm -f "$D/.completed/step-5c-terminal"
terminal_probe_step5c='test -f "${DESIGN_TMPDIR}/.completed/step-5c-terminal" && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$terminal_probe_step5c" "$D")")
assert_allow "$out" 'absent Step 5c terminal sentinel foreground probe allows'

write_marker $$ "$(date +%s)" 21600 design-step-final-summary
rm -f "$D/.completed/step-final-summary"
terminal_probe_summary="DESIGN_TMPDIR=$D; [ -f \"\$DESIGN_TMPDIR/.completed/step-final-summary\" ] && echo DONE || echo WAIT"
out=$(run_payload "$(payload_bash "$terminal_probe_summary" "$D")")
assert_allow "$out" 'absent final-summary terminal sentinel foreground probe allows with tmpdir assignment'

write_marker $$ "$(date +%s)" 21600 design-step5c
nonterminal_step5c_probe='test -f "${DESIGN_TMPDIR}/.completed/step-5c" && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$nonterminal_step5c_probe" "$D")")
assert_deny "$out" 'foreground probe of non-terminal Step 5c sentinel denies' "$EXPECTED_STEP"

write_marker $$ "$(date +%s)" 21600 design-step3-review
nonterminal_step3_probe='test -f "${DESIGN_TMPDIR}/.completed/step-3" && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$nonterminal_step3_probe" "$D")")
assert_deny "$out" 'foreground probe of non-terminal Step 3 sentinel denies' "$EXPECTED_STEP"

write_marker $$ "$(date +%s)" 21600 design-step3-review
nonterminal_step35_probe='[[ -f "${DESIGN_TMPDIR}/.completed/step-3.5" ]] && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$nonterminal_step35_probe" "$D")")
assert_deny "$out" 'foreground probe of Step 3.5 sentinel denies' "$EXPECTED_STEP"

write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
reset_probe_counters
terminal_probe_step3_dbl='[[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]] && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$terminal_probe_step3_dbl" "$D")")
assert_allow "$out" 'double-bracket Step 3 terminal sentinel foreground probe allows'

write_marker $$ "$(date +%s)" 21600 design-step3-review
mkdir -p "$D/.completed"
: >"$D/.completed/step-3"
rm -f "$D/.completed/step-3-terminal"
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'stale step-3 milestone without step-3-terminal does not release marker' "$EXPECTED_STEP"
rm -f "$D/.completed/step-3"
write_marker $$ "$(date +%s)" 21600 design-step3-review

sentinel_probe_sleep='test -f "${DESIGN_TMPDIR}/.completed/step-3-terminal" && sleep 1'
out=$(run_payload "$(payload_bash "$sentinel_probe_sleep" "$D")")
assert_deny "$out" 'foreground terminal sentinel probe plus sleep denies' "$EXPECTED_STEP"

sentinel_probe_until='until [ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]; do :; done'
out=$(run_payload "$(payload_bash "$sentinel_probe_until" "$D")")
assert_deny "$out" 'foreground terminal sentinel probe wrapped in until denies' "$EXPECTED_STEP"

sentinel_probe_while='while [ ! -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]; do :; done'
out=$(run_payload "$(payload_bash "$sentinel_probe_while" "$D")")
assert_deny "$out" 'foreground terminal sentinel probe wrapped in while denies' "$EXPECTED_STEP"

result_env_probe='test -f "$DESIGN_TMPDIR/.step3-review-result.env" && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$result_env_probe" "$D")")
assert_deny "$out" 'foreground probe of Step 3 result env denies' "$EXPECTED_STEP"

publish_env_probe='test -f "$DESIGN_TMPDIR/.design-publish-result.env" && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$publish_env_probe" "$D")")
assert_deny "$out" 'foreground probe of publish result env denies' "$EXPECTED_STEP"

for verb in cat ls stat jq; do
  appended_probe="test -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" && $verb \"\$DESIGN_TMPDIR/.step3-review-result.env\""
  out=$(run_payload "$(payload_bash "$appended_probe" "$D")")
  assert_deny "$out" "foreground terminal sentinel probe with appended $verb denies" "$EXPECTED_STEP"
done

cmd_sub_probe='[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo DONE || echo $(cat "$DESIGN_TMPDIR/.step3-review-result.env")'
out=$(run_payload "$(payload_bash "$cmd_sub_probe" "$D")")
assert_deny "$out" 'foreground terminal sentinel probe with command substitution in echo tail denies' "$EXPECTED_STEP"

# #5610: a compound probe referencing BOTH a tasks output file (which excludes it from the
# simple foreground-probe classifier at bash_is_terminal_sentinel_foreground_probe) AND the
# .completed/step-3-terminal sentinel must still deny through the generic deny path
# (bash_has_probe_verb + bash_has_probe_target). This is the exact bypass shape from the
# bug: wc -c on the task output file combined with a terminal-sentinel file test in one
# compound command.
write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
compound_taskoutput_sentinel_probe='wc -c "$DESIGN_TMPDIR/tasks/foo.output" && [ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]'
out=$(run_payload "$(payload_bash "$compound_taskoutput_sentinel_probe" "$D")")
assert_deny "$out" 'compound tasks/output plus terminal-sentinel probe denies via generic path' "$EXPECTED_STEP"

informal_probe="DESIGN_TMPDIR=/tmp/informal-design; [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ] && echo DONE || echo WAIT"
out=$(run_payload "$(payload_bash "$informal_probe" "$D")")
assert_deny "$out" 'foreground probe with DESIGN_TMPDIR outside live marker dir denies' "$EXPECTED_STEP"

D_INFORMAL="$TMP/informal-design"
mkdir -p "$D_INFORMAL"
MARKER_SAVE="$MARKER"
MARKER="$D_INFORMAL/.bg-wait-active"
write_marker $$ "$(date +%s)" 21600 design-step3-review
informal_allow="DESIGN_TMPDIR=$D_INFORMAL; [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ] && echo DONE || echo WAIT"
out=$(printf '%s' "$(payload_bash "$informal_allow" "$D_INFORMAL")" | LARCH_BG_POLL_GUARD_MARKER="$MARKER" "$HOOK")
assert_allow "$out" 'foreground probe allows DESIGN_TMPDIR path containing informal substring when bound to live dir'
MARKER="$MARKER_SAVE"
rm -rf "$D_INFORMAL"

touch_forgery="touch \"\$DESIGN_TMPDIR/.completed/step-3-terminal\""
out=$(run_payload "$(payload_bash "$touch_forgery" "$D")")
assert_deny "$out" 'live marker plus touch of terminal sentinel denies' "$EXPECTED_STEP"

for alt_forgery in \
  ': >"\$DESIGN_TMPDIR/.completed/step-3-terminal"' \
  'printf x > "\$DESIGN_TMPDIR/.completed/step-3-terminal"' \
  'cp /etc/hosts "\$DESIGN_TMPDIR/.completed/step-3-terminal"' \
  'mv /etc/hosts "\$DESIGN_TMPDIR/.completed/step-3-terminal"' \
  'ln /etc/hosts "\$DESIGN_TMPDIR/.completed/step-3-terminal"' \
  'tee "\$DESIGN_TMPDIR/.completed/step-3-terminal" </etc/hosts' \
  'install /etc/hosts "\$DESIGN_TMPDIR/.completed/step-3-terminal"'
do
  out=$(run_payload "$(payload_bash "$alt_forgery" "$D")")
  assert_deny "$out" "live marker plus alternate sentinel forgery denies: $alt_forgery" "$EXPECTED_STEP"
done

sidecar_forgery=': >"\$DESIGN_TMPDIR/.step3-terminal-persisted-this-run"'
out=$(run_payload "$(payload_bash "$sidecar_forgery" "$D")")
assert_deny "$out" 'live marker plus sidecar forgery denies' "$EXPECTED_STEP"

mkdir -p "$D/.completed"
write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
: >"$D/.completed/real-terminal-target"
ln -s "$D/.completed/real-terminal-target" "$D/.completed/step-3-terminal"
out=$(run_payload "$(payload_bash "$terminal_probe_step3" "$D")")
assert_deny "$out" 'symlinked terminal sentinel foreground probe denies' "$EXPECTED_STEP"
rm -f "$D/.completed/step-3-terminal"

write_marker $$ "$(date +%s)" 21600 design-step5c
: >"$D/.completed/step-5c"
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'Step 5c non-terminal sentinel does not release marker' "$EXPECTED_STEP"
: >"$D/.completed/step-5c-terminal"
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'Step 5c terminal sentinel releases marker'
rm -f "$D/.completed/step-5c" "$D/.completed/step-5c-terminal"

out=$(run_payload "$(payload_bash "rg plan-review docs/" "/tmp/other-repo")")
assert_allow "$out" 'plan-review substring outside live tmpdir allows'

out=$(run_payload "$(payload_bash "awk '{print}' \"\$DESIGN_TMPDIR/plan-review/round-1/foo-output.txt\"")")
assert_deny "$out" 'live marker plus awk against DESIGN_TMPDIR output denies' "$EXPECTED_STEP"

# #5684: production-divergence regression. In production the hook's PPID/input never
# match the marker's stored CLAUDE_PID and LARCH_BG_POLL_GUARD_SESSION_PID is unset, so
# the old CLAUDE_PID equality check rejected every marker and the guard never fired. A
# live marker (alive PID, within age) must now deny regardless of the stored CLAUDE_PID,
# with no session-PID env set. This is exactly the real hook environment.
EXPECTED_STEP=design-step3-review
printf '%s\n' "PID=$$" "CLAUDE_PID=999999999" "START_EPOCH=$(date +%s)" "STEP=design-step3-review" "TIMEOUT_S=21600" >"$MARKER"
out=$(printf '%s' "$(payload_bash "$design_tmpdir_ls")" | LARCH_BG_POLL_GUARD_MARKER="$MARKER" "$HOOK")
assert_deny "$out" 'live marker denies regardless of stored CLAUDE_PID without session-PID env (#5684)' "$EXPECTED_STEP"
write_marker $$ "$(date +%s)"
printf '0\n' >"$D/bg-poll-guard-denials.count"
chmod 444 "$D/bg-poll-guard-denials.count" 2>/dev/null || true
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
chmod 644 "$D/bg-poll-guard-denials.count" 2>/dev/null || true
assert_deny "$out" 'deny JSON emitted even when telemetry count write fails' "$EXPECTED_STEP"

out=$(printf '{not-json' | LARCH_BG_POLL_GUARD_MARKER="$MARKER" "$HOOK")
assert_allow "$out" 'malformed JSON silently allows'

NOJQ="$TMP/nojq-bin"
mkdir -p "$NOJQ"
ln -s /bin/cat "$NOJQ/cat"
ln -s "$(command -v bash)" "$NOJQ/bash"
out=$(printf '%s' "$(payload_bash "$design_tmpdir_ls")" | PATH="$NOJQ" LARCH_BG_POLL_GUARD_MARKER="$MARKER" "$HOOK" 2>/dev/null || true)
assert_allow "$out" 'missing jq path silently allows'

out=$(run_payload "$(payload_bash 'grep foo final-summary.md' "$D")")
assert_deny "$out" 'deny JSON carries PreToolUse and permissionDecision=deny' "$EXPECTED_STEP"

count=$(awk 'NR==1 { print; exit }' "$D/bg-poll-guard-denials.count" 2>/dev/null || printf '0')
case "$count" in ''|*[!0-9]*) count=0 ;; esac
if [ "$count" -gt 0 ]; then
  pass 'telemetry count increments on denial'
else
  fail 'telemetry count must increment on denial'
fi

# #4431 Fix A: same-turn completion release. A live design-step3-review marker
# whose terminal completion sentinel (.completed/step-3-terminal) already exists is
# treated as resolved, so the orchestrator can read the result artifact in the
# same turn the <task-notification> fired — before the bg process's EXIT trap
# removes the marker.
mkdir -p "$D/.completed"
write_marker $$ "$(date +%s)" 21600 design-step3-review
: >"$D/.completed/step-3-terminal"
: >"$D/.step3-terminal-persisted-this-run"
out=$(run_payload "$(payload_read "$D/.step3-review-result.env")")
assert_allow "$out" 'step3 terminal completion sentinel releases Read of result env'
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'step3 terminal completion sentinel releases Bash probe'

write_marker $$ "$(date +%s)" 21600 design-step3-review
: >"$D/.completed/step-3-terminal"
rm -f "$D/.step3-terminal-persisted-this-run"
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'step3 terminal sentinel without persist sidecar does not release marker' "$EXPECTED_STEP"
rm -f "$D/.completed/step-3-terminal" "$MARKER"

write_marker $$ "$(date +%s)" 21600 design-step5c
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'step-3-terminal sentinel does not release a non-step3 marker' "$EXPECTED_STEP"

write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
: >"$D/.completed/real-target"
ln -s "$D/.completed/real-target" "$D/.completed/step-3-terminal"
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'symlinked completion sentinel does not release' "$EXPECTED_STEP"
rm -f "$D/.completed/step-3-terminal" "$MARKER"

# #4450: extend the same-turn completion release to design-step5c and
# design-step-final-summary. Each wrapper writes its terminal sentinel
# (.completed/step-5c-terminal / .completed/step-final-summary) before the bg
# process exits, so a live marker for either step is released once that sentinel
# exists — mirroring the design-step3-review coverage above.
mkdir -p "$D/.completed"
write_marker $$ "$(date +%s)" 21600 design-step5c
: >"$D/.completed/step-5c-terminal"
out=$(run_payload "$(payload_read "$D/.design-publish-result.env")")
assert_allow "$out" 'step5c completion sentinel releases Read of result env'
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'step5c completion sentinel releases Bash probe'
rm -f "$D/.completed/step-5c-terminal" "$MARKER"

write_marker $$ "$(date +%s)" 21600 design-step-final-summary
: >"$D/.completed/step-final-summary"
out=$(run_payload "$(payload_read "$D/final-summary.md")")
assert_allow "$out" 'final-summary completion sentinel releases Read of result artifact'
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'final-summary completion sentinel releases Bash probe'
rm -f "$D/.completed/step-final-summary" "$MARKER"

# #5478: consecutive foreground-probe clamp. The valid recovery pattern is one
# foreground probe per real <task-notification>; spurious empty-output notifications
# (#5240) can drive repeated probes against a still-absent sentinel. After the
# threshold the guard denies further probes until the sentinel appears, keyed per
# sentinel so other waits in the same tmpdir are unaffected, and the count resets once
# the sentinel (and Step 3 sidecar) is present.
reset_probe_counters
write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
probe_clamp_cmd='[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_allow "$out" 'probe clamp: 1st foreground probe allows'
out=$(run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_allow "$out" 'probe clamp: 2nd foreground probe allows'
out=$(run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_deny "$out" 'probe clamp: 3rd consecutive probe against absent sentinel denies' "$EXPECTED_STEP"
out=$(run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_deny "$out" 'probe clamp: stays denied while sentinel absent' "$EXPECTED_STEP"

# Per-sentinel isolation: a Step 5c probe is unaffected by the tripped step-3 clamp.
write_marker $$ "$(date +%s)" 21600 design-step5c
rm -f "$D/.completed/step-5c-terminal"
probe_clamp_5c='test -f "$DESIGN_TMPDIR/.completed/step-5c-terminal" && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$probe_clamp_5c" "$D")")
assert_allow "$out" 'probe clamp: distinct sentinel counter is isolated (step5c allows)'

# Reset on sentinel present: once the terminal sentinel (and Step 3 sidecar) exists,
# the marker releases and the clamp counter clears so a later wait starts fresh.
write_marker $$ "$(date +%s)" 21600 design-step3-review
mkdir -p "$D/.completed"
: >"$D/.completed/step-3-terminal"
: >"$D/.step3-terminal-persisted-this-run"
out=$(run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_allow "$out" 'probe clamp: sentinel present releases marker and allows probe'
if [ ! -e "$D/bg-poll-guard-probe-denials.step-3-terminal.count" ]; then
  pass 'probe clamp: counter file cleared once sentinel present'
else
  fail 'probe clamp: counter file must clear once sentinel present'
fi
rm -f "$D/.completed/step-3-terminal" "$D/.step3-terminal-persisted-this-run" "$MARKER"

# Threshold override: LARCH_BG_POLL_GUARD_PROBE_THRESHOLD tightens the clamp.
reset_probe_counters
write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
out=$(LARCH_BG_POLL_GUARD_PROBE_THRESHOLD=1 run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_allow "$out" 'probe clamp: threshold=1 allows 1st probe'
out=$(LARCH_BG_POLL_GUARD_PROBE_THRESHOLD=1 run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_deny "$out" 'probe clamp: threshold=1 denies 2nd probe' "$EXPECTED_STEP"
reset_probe_counters
rm -f "$MARKER"

# Stale counter clears when a dead marker is removed, so a relaunched wait can probe.
write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
out=$(run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_allow "$out" 'probe clamp: pre-relaunch 1st probe allows'
out=$(run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_allow "$out" 'probe clamp: pre-relaunch 2nd probe allows'
out=$(run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_deny "$out" 'probe clamp: pre-relaunch 3rd probe denies' "$EXPECTED_STEP"
write_marker 999999 "$(date +%s)" 21600 design-step3-review
out=$(run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_allow "$out" 'probe clamp: dead marker removal clears counter sidecar'
write_marker $$ "$(date +%s)" 21600 design-step3-review
out=$(run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_allow "$out" 'probe clamp: fresh marker after dead removal allows 1st probe'
rm -f "$MARKER"

# Parallel live tmpdirs: clamp counters stay scoped to the probed dir only.
SESSIONS="$HOME/.cache/larch/sessions"
D_A="$SESSIONS/wait-a"
D_B="$SESSIONS/wait-b"
mkdir -p "$D_A/.completed" "$D_B/.completed"
MARKER_A="$D_A/.bg-wait-active"
MARKER_B="$D_B/.bg-wait-active"
write_marker_at "$MARKER_A" $$ "$(date +%s)" 21600 design-step3-review
write_marker_at "$MARKER_B" $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D_A/.completed/step-3-terminal" "$D_B/.completed/step-3-terminal" \
  "$D_A"/bg-poll-guard-probe-denials.*.count "$D_B"/bg-poll-guard-probe-denials.*.count
probe_clamp_a="DESIGN_TMPDIR=$D_A; [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ] && echo DONE || echo WAIT"
probe_clamp_b="DESIGN_TMPDIR=$D_B; [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ] && echo DONE || echo WAIT"
out=$(run_payload_auto_markers "$(payload_bash "$probe_clamp_a" "$D_A")")
assert_allow "$out" 'parallel clamp: dir A 1st probe allows'
out=$(run_payload_auto_markers "$(payload_bash "$probe_clamp_a" "$D_A")")
assert_allow "$out" 'parallel clamp: dir A 2nd probe allows'
out=$(run_payload_auto_markers "$(payload_bash "$probe_clamp_a" "$D_A")")
assert_deny "$out" 'parallel clamp: dir A 3rd probe denies' "$EXPECTED_STEP"
out=$(run_payload_auto_markers "$(payload_bash "$probe_clamp_b" "$D_B")")
assert_allow "$out" 'parallel clamp: dir B unaffected after dir A clamp tripped'
rm -f "$MARKER_A" "$MARKER_B" \
  "$D_A"/bg-poll-guard-probe-denials.*.count "$D_B"/bg-poll-guard-probe-denials.*.count

# TMPDIR claude-implement-* fallback discovery without marker override.
D_IMPL="$TMP/claude-implement-fallback-xyz"
mkdir -p "$D_IMPL/.completed"
MARKER_IMPL="$D_IMPL/.bg-wait-active"
write_marker_at "$MARKER_IMPL" $$ "$(date +%s)" 21600 implement-step3-checks
out=$(run_payload_auto_markers "$(payload_monitor "$D_IMPL")")
assert_deny "$out" 'TMPDIR claude-implement-* fallback discovery without marker override denies Monitor' "$EXPECTED_STEP"
rm -f "$MARKER_IMPL"

# Many TMPDIR larch-*/claude-*-prefixed dirs stay well under the hook's 10s PreToolUse
# budget and discovery still finds the live marker (#5943 regression guard:
# marker_candidates() used to spawn one find subprocess per matched dir).
mkdir -p "$TMP"/larch-perf-{1..3000}
D_PERF="$TMP/claude-implement-perf-xyz"
mkdir -p "$D_PERF/.completed"
MARKER_PERF="$D_PERF/.bg-wait-active"
write_marker_at "$MARKER_PERF" $$ "$(date +%s)" 21600 implement-step3-checks
start_ts=$(date +%s)
out=$(run_payload_auto_markers "$(payload_monitor "$D_PERF")")
elapsed=$(( $(date +%s) - start_ts ))
assert_deny "$out" '#5943: discovery over 3000 TMPDIR session dirs still denies Monitor' "$EXPECTED_STEP"
if [ "$elapsed" -le 5 ]; then
  pass "#5943: discovery over 3000 TMPDIR session dirs stays bounded (elapsed=${elapsed}s)"
else
  fail "#5943: discovery over 3000 TMPDIR session dirs exceeded bound (elapsed=${elapsed}s, want <=5s)"
fi
rm -f "$MARKER_PERF"
rm -rf "$TMP"/larch-perf-*

# Monitor and TaskOutput are always denied while any live marker is active.
write_marker $$ "$(date +%s)" 21600 design-step3-review
out=$(run_payload "$(payload_monitor)")
assert_deny "$out" 'live design marker plus Monitor denies' "$EXPECTED_STEP"

out=$(run_payload "$(payload_taskoutput)")
assert_deny "$out" 'live design marker plus TaskOutput denies' "$EXPECTED_STEP"

# Implement bg-wait markers: implement-step3-checks and implement-step5-review.
write_marker $$ "$(date +%s)" 21600 implement-step3-checks
out=$(run_payload "$(payload_monitor)")
assert_deny "$out" 'live implement-step3-checks marker plus Monitor denies' "$EXPECTED_STEP"

out=$(run_payload "$(payload_taskoutput)")
assert_deny "$out" 'live implement-step3-checks marker plus TaskOutput denies' "$EXPECTED_STEP"

out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'live implement-step3-checks marker denies Bash probe' "$EXPECTED_STEP"

# implement-step3-checks terminal sentinel releases the marker.
mkdir -p "$D/.completed"
write_marker $$ "$(date +%s)" 21600 implement-step3-checks
: >"$D/.completed/step-3-terminal"
out=$(run_payload "$(payload_monitor)")
assert_allow "$out" 'implement-step3-checks step-3-terminal sentinel releases Monitor'
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'implement-step3-checks step-3-terminal sentinel releases Bash probe'
rm -f "$D/.completed/step-3-terminal" "$MARKER"

# /implement Step 3 foreground terminal-sentinel probe carve-out. This path is
# allowed only for the exact `test -f` shape after a genuine completion-notification
# read was denied, and it is clamped while the sentinel is absent.
write_marker $$ "$(date +%s)" 21600 implement-step3-checks
rm -f "$D/.completed/step-3-terminal" "$D"/bg-poll-guard-probe-denials.step-3-terminal.count
implement_step3_probe='test -f "$IMPLEMENT_TMPDIR/.completed/step-3-terminal"'
implement_step3_probe_braced='test -f "${IMPLEMENT_TMPDIR}/.completed/step-3-terminal"'
implement_step3_probe_prefixed="IMPLEMENT_TMPDIR=$D; test -f \"\$IMPLEMENT_TMPDIR/.completed/step-3-terminal\""
out=$(run_payload "$(payload_bash "$implement_step3_probe_braced" "$D")")
assert_allow "$out" 'implement Step 3 terminal probe braced form allows while sentinel absent'
rm -f "$D"/bg-poll-guard-probe-denials.step-3-terminal.count
out=$(run_payload "$(payload_bash "$implement_step3_probe_prefixed" "$D")")
assert_allow "$out" 'implement Step 3 terminal probe with IMPLEMENT_TMPDIR prefix allows while sentinel absent'
rm -f "$D"/bg-poll-guard-probe-denials.step-3-terminal.count
out=$(run_payload "$(payload_bash "$implement_step3_probe" "$D")")
assert_allow "$out" 'implement Step 3 terminal probe allows while absent, first attempt'
out=$(run_payload "$(payload_bash "$implement_step3_probe" "$D")")
assert_allow "$out" 'implement Step 3 terminal probe allows while absent, second attempt'
out=$(run_payload "$(payload_bash "$implement_step3_probe" "$D")")
assert_deny "$out" 'implement Step 3 terminal probe clamps repeated absent probes' "$EXPECTED_STEP"
: >"$D/.completed/step-3-terminal"
out=$(run_payload "$(payload_bash "$implement_step3_probe" "$D")")
assert_allow "$out" 'implement Step 3 terminal sentinel presence releases marker and allows probe'
if [ ! -e "$D/bg-poll-guard-probe-denials.step-3-terminal.count" ]; then
  pass 'implement Step 3 terminal sentinel presence clears clamp counter file'
else
  fail 'implement Step 3 terminal sentinel presence must clear clamp counter file'
fi
rm -f "$D/.completed/step-3-terminal" "$MARKER"

write_marker $$ "$(date +%s)" 21600 implement-step5-review
out=$(run_payload "$(payload_bash "$implement_step3_probe" "$D")")
assert_deny "$out" 'implement Step 3 terminal probe bound to Step 5 marker denies' "$EXPECTED_STEP"
rm -f "$MARKER"

# implement-step5-review marker and terminal sentinel.
write_marker $$ "$(date +%s)" 21600 implement-step5-review
out=$(run_payload "$(payload_monitor)")
assert_deny "$out" 'live implement-step5-review marker plus Monitor denies' "$EXPECTED_STEP"

out=$(run_payload "$(payload_taskoutput)")
assert_deny "$out" 'live implement-step5-review marker plus TaskOutput denies' "$EXPECTED_STEP"

# IMPLEMENT_TMPDIR reference in Bash probe is denied when implement marker is live.
implement_probe='ls "$IMPLEMENT_TMPDIR"'
out=$(run_payload "$(payload_bash "$implement_probe")")
assert_deny "$out" 'live implement-step5-review marker plus Bash ls IMPLEMENT_TMPDIR denies' "$EXPECTED_STEP"

# implement-step5-review terminal sentinel releases the marker.
write_marker $$ "$(date +%s)" 21600 implement-step5-review
: >"$D/.completed/step-5-terminal"
out=$(run_payload "$(payload_monitor)")
assert_allow "$out" 'implement-step5-review step-5-terminal sentinel releases Monitor'
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'implement-step5-review step-5-terminal sentinel releases Bash probe'
rm -f "$D/.completed/step-5-terminal" "$MARKER"

# /implement Step 5 foreground terminal-sentinel probe carve-out mirrors Step 3
# but binds only to implement-step5-review markers and .completed/step-5-terminal.
write_marker $$ "$(date +%s)" 21600 implement-step5-review
rm -f "$D/.completed/step-5-terminal" "$D"/bg-poll-guard-probe-denials.step-5-terminal.count
implement_step5_probe='test -f "$IMPLEMENT_TMPDIR/.completed/step-5-terminal"'
implement_step5_probe_braced='test -f "${IMPLEMENT_TMPDIR}/.completed/step-5-terminal"'
implement_step5_probe_prefixed="IMPLEMENT_TMPDIR=$D; test -f \"\$IMPLEMENT_TMPDIR/.completed/step-5-terminal\""
out=$(run_payload "$(payload_bash "$implement_step5_probe_braced" "$D")")
assert_allow "$out" 'implement Step 5 terminal probe braced form allows while sentinel absent'
rm -f "$D"/bg-poll-guard-probe-denials.step-5-terminal.count
out=$(run_payload "$(payload_bash "$implement_step5_probe_prefixed" "$D")")
assert_allow "$out" 'implement Step 5 terminal probe with IMPLEMENT_TMPDIR prefix allows while sentinel absent'
rm -f "$D"/bg-poll-guard-probe-denials.step-5-terminal.count
out=$(run_payload "$(payload_bash "$implement_step5_probe" "$D")")
assert_allow "$out" 'implement Step 5 terminal probe allows while absent, first attempt'
out=$(run_payload "$(payload_bash "$implement_step5_probe" "$D")")
assert_allow "$out" 'implement Step 5 terminal probe allows while absent, second attempt'
out=$(run_payload "$(payload_bash "$implement_step5_probe" "$D")")
assert_deny "$out" 'implement Step 5 terminal probe clamps repeated absent probes' "$EXPECTED_STEP"
: >"$D/.completed/step-5-terminal"
out=$(run_payload "$(payload_bash "$implement_step5_probe" "$D")")
assert_allow "$out" 'implement Step 5 terminal sentinel presence releases marker and allows probe'
if [ ! -e "$D/bg-poll-guard-probe-denials.step-5-terminal.count" ]; then
  pass 'implement Step 5 terminal sentinel presence clears clamp counter file'
else
  fail 'implement Step 5 terminal sentinel presence must clear clamp counter file'
fi
rm -f "$D/.completed/step-5-terminal" "$MARKER"

write_marker $$ "$(date +%s)" 21600 implement-step3-checks
out=$(run_payload "$(payload_bash "$implement_step5_probe" "$D")")
assert_deny "$out" 'implement Step 5 terminal probe bound to Step 3 marker denies' "$EXPECTED_STEP"
rm -f "$MARKER"

write_marker $$ "$(date +%s)" 21600 implement-step5-review
implement_step5_appended='test -f "$IMPLEMENT_TMPDIR/.completed/step-5-terminal" && cat "$IMPLEMENT_TMPDIR/tasks/foo.output"'
out=$(run_payload "$(payload_bash "$implement_step5_appended" "$D")")
assert_deny "$out" 'implement Step 5 terminal probe with appended cat denies' "$EXPECTED_STEP"
implement_step5_bracket='[ -f "$IMPLEMENT_TMPDIR/.completed/step-5-terminal" ]'
out=$(run_payload "$(payload_bash "$implement_step5_bracket" "$D")")
assert_deny "$out" 'implement Step 5 bracket terminal probe remains denied' "$EXPECTED_STEP"
touch_step5_terminal='touch "$IMPLEMENT_TMPDIR/.completed/step-5-terminal"'
out=$(run_payload "$(payload_bash "$touch_step5_terminal" "$D")")
assert_deny "$out" 'live Step 5 marker plus touch terminal sentinel forgery denies' "$EXPECTED_STEP"
truncate_step5_terminal=': >"$IMPLEMENT_TMPDIR/.completed/step-5-terminal"'
out=$(run_payload "$(payload_bash "$truncate_step5_terminal" "$D")")
assert_deny "$out" 'live Step 5 marker plus truncate terminal sentinel forgery denies' "$EXPECTED_STEP"
rm -f "$MARKER"

# implement-step8-ship marker, rc release sentinel, and sanctioned rc probe.
rm -f "$D/.step-8-ship-handoff.rc" "$D/bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count" "$MARKER"
write_marker $$ "$(date +%s)" 21600 implement-step8-ship
out=$(run_payload "$(payload_monitor)")
assert_deny "$out" 'live implement-step8-ship marker plus Monitor denies' "$EXPECTED_STEP"
out=$(run_payload "$(payload_taskoutput)")
assert_deny "$out" 'live implement-step8-ship marker plus TaskOutput denies' "$EXPECTED_STEP"
step8_ordinary_probe='ls "$IMPLEMENT_TMPDIR"'
out=$(run_payload "$(payload_bash "$step8_ordinary_probe")")
assert_deny "$out" 'live implement-step8-ship marker plus ordinary IMPLEMENT_TMPDIR probe denies' "$EXPECTED_STEP"
step8_rc_probe='test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"'
step8_rc_probe_braced='test -f "${IMPLEMENT_TMPDIR}/.step-8-ship-handoff.rc"'
step8_rc_probe_pointer='IMPLEMENT_TMPDIR=$(awk '\''BEGIN{p="IMPLEMENT_TMPDIR="} index($0,p)==1{print substr($0,length(p)+1); exit}'\'' "$HOME/.cache/larch/sessions/current-implement-env-$PPID.sh" 2>/dev/null); test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"'
out=$(run_payload "$(payload_bash "$step8_rc_probe_braced" "$D")")
assert_allow "$out" 'Step 8 handoff rc braced probe allows while rc absent'
rm -f "$D/bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count"
out=$(run_payload "$(payload_bash "$step8_rc_probe_pointer" "$D")")
assert_allow "$out" 'Step 8 handoff rc pointer-resolved probe allows while rc absent'
rm -f "$D/bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count"
out=$(run_payload "$(payload_bash "$step8_rc_probe" "$D")")
assert_allow "$out" 'Step 8 handoff rc probe allows while rc absent, first attempt'
out=$(run_payload "$(payload_bash "$step8_rc_probe" "$D")")
assert_allow "$out" 'Step 8 handoff rc probe allows while rc absent, second attempt'
out=$(run_payload "$(payload_bash "$step8_rc_probe" "$D")")
assert_deny "$out" 'Step 8 handoff rc probe denies after clamp threshold' "$EXPECTED_STEP"
: >"$D/.step-8-ship-handoff.rc"
out=$(run_payload "$(payload_bash "$step8_rc_probe" "$D")")
assert_allow "$out" 'Step 8 handoff rc presence clears clamp and allows probe'
if [ ! -e "$D/bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count" ]; then
  pass 'Step 8 handoff rc presence clears clamp counter file'
else
  fail 'Step 8 handoff rc presence must clear clamp counter file'
fi
out=$(run_payload "$(payload_monitor)")
assert_allow "$out" 'Step 8 handoff rc releases marker and allows Monitor'
rm -f "$D/.step-8-ship-handoff.rc" "$MARKER"

write_marker $$ "$(date +%s)" 21600 implement-step8-ship
: >"$D/.step-8-real-rc"
ln -s "$D/.step-8-real-rc" "$D/.step-8-ship-handoff.rc"
out=$(run_payload "$(payload_monitor)")
assert_deny "$out" 'symlinked Step 8 handoff rc does not release marker' "$EXPECTED_STEP"
out=$(run_payload "$(payload_bash "$step8_rc_probe" "$D")")
assert_deny "$out" 'symlinked Step 8 handoff rc probe denies' "$EXPECTED_STEP"
rm -f "$D/.step-8-ship-handoff.rc" "$D/.step-8-real-rc" "$MARKER"

write_marker $$ "$(date +%s)" 21600 implement-step5-review
out=$(run_payload "$(payload_bash "$step8_rc_probe" "$D")")
assert_deny "$out" 'Step 8 handoff rc probe under implement-step5-review marker denies' "$EXPECTED_STEP"
rm -f "$MARKER"

touch_step8_rc='touch "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"'
write_marker $$ "$(date +%s)" 21600 implement-step8-ship
out=$(run_payload "$(payload_bash "$touch_step8_rc" "$D")")
assert_deny "$out" 'live Step 8 marker plus touch rc forgery denies' "$EXPECTED_STEP"
truncate_step8_rc=': >"$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"'
out=$(run_payload "$(payload_bash "$truncate_step8_rc" "$D")")
assert_deny "$out" 'live Step 8 marker plus truncate rc forgery denies' "$EXPECTED_STEP"
touch_step8_rc_cwd='touch .step-8-ship-handoff.rc'
out=$(run_payload "$(payload_bash "$touch_step8_rc_cwd" "$D")")
assert_deny "$out" 'live Step 8 marker plus cwd-relative touch rc forgery denies' "$EXPECTED_STEP"
truncate_step8_rc_cwd=': > .step-8-ship-handoff.rc'
out=$(run_payload "$(payload_bash "$truncate_step8_rc_cwd" "$D")")
assert_deny "$out" 'live Step 8 marker plus cwd-relative truncate rc forgery denies' "$EXPECTED_STEP"
rm -f "$D/.step-8-ship-handoff.rc" "$MARKER"

D_STEP5="$SESSIONS/wait-step5"
D_STEP8="$SESSIONS/wait-step8"
mkdir -p "$D_STEP5/.completed" "$D_STEP8/.completed"
MARKER_STEP5="$D_STEP5/.bg-wait-active"
MARKER_STEP8="$D_STEP8/.bg-wait-active"
write_marker_at "$MARKER_STEP5" $$ "$(date +%s)" 21600 implement-step5-review
write_marker_at "$MARKER_STEP8" $$ "$(date +%s)" 21600 implement-step8-ship
multi_step8_probe="IMPLEMENT_TMPDIR=$D_STEP8; test -f \"\$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc\""
out=$(run_payload_auto_markers "$(payload_bash "$multi_step8_probe" "$D_STEP8")")
assert_allow "$out" 'parallel markers bind Step 8 rc probe to Step 8 tmpdir and allow'
wrong_step8_probe="IMPLEMENT_TMPDIR=$D_STEP5; test -f \"\$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc\""
out=$(run_payload_auto_markers "$(payload_bash "$wrong_step8_probe" "$D_STEP5")")
assert_deny "$out" 'parallel markers deny Step 8 rc probe bound to non-Step 8 tmpdir' implement-step5-review
rm -f "$MARKER_STEP5" "$MARKER_STEP8" "$D_STEP8/bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count"

write_marker $$ "$(date +%s)" 21600 implement-step8-ship
printf '99\n' >"$D/bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count"
rm -f "$D/bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count"
out=$(run_payload "$(payload_bash "$step8_rc_probe" "$D")")
assert_allow "$out" 'Step 8 same-tmpdir relaunch with wrapper-cleared clamp allows first rc probe'
rm -f "$MARKER"

for spec in \
  'design-step4-tail:.completed/step-4:design' \
  'implement-step5-resume:.completed/step-5-resume-terminal:implement' \
  'implement-step5-self-review:.completed/step-5-self-review-terminal:implement' \
  'implement-step6-checks:.completed/step-6-terminal:implement' \
  'implement-step7a:.completed/step-7a-terminal:implement'
do
  step=${spec%%:*}
  rest=${spec#*:}
  sentinel=${rest%%:*}
  kind=${rest#*:}
  rm -f "$MARKER" "$D/.completed/"* "$D"/bg-poll-guard-probe-denials.*.count
  mkdir -p "$D/.completed"
  write_marker $$ "$(date +%s)" 21600 "$step"
  out=$(run_payload "$(payload_monitor)")
  assert_deny "$out" "live $step marker plus Monitor denies" "$EXPECTED_STEP"
  out=$(run_payload "$(payload_taskoutput)")
  assert_deny "$out" "live $step marker plus TaskOutput denies" "$EXPECTED_STEP"
  out=$(run_payload "$(payload_bash "$implement_probe" "$D")")
  assert_deny "$out" "live $step marker plus ordinary tmpdir probe denies" "$EXPECTED_STEP"
  : >"$D/$sentinel"
  out=$(run_payload "$(payload_monitor)")
  assert_allow "$out" "$step terminal sentinel releases Monitor"
  rm -f "$D/$sentinel"
  : >"$D/.completed/real-target"
  ln -s "$D/.completed/real-target" "$D/$sentinel"
  out=$(run_payload "$(payload_monitor)")
  assert_deny "$out" "symlinked $step terminal sentinel does not release" "$EXPECTED_STEP"
  rm -f "$D/$sentinel" "$D/.completed/real-target" "$MARKER"
  if [ "$kind" = implement ]; then
    terminal_basename=${sentinel##*/}
    impl_terminal_probe="test -f \"\$IMPLEMENT_TMPDIR/.completed/$terminal_basename\""
    write_marker $$ "$(date +%s)" 21600 "$step"
    out=$(run_payload "$(payload_bash "$impl_terminal_probe" "$D")")
    assert_deny "$out" "$step does not gain an implement foreground terminal-probe carve-out" "$EXPECTED_STEP"
    rm -f "$MARKER"
  fi
done

write_marker $$ "$(date +%s)" 21600 design-step4-tail
rm -f "$D/.completed/step-4"
reset_probe_counters
step4_foreground_probe='[ -f "$DESIGN_TMPDIR/.completed/step-4" ] && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$step4_foreground_probe" "$D")")
assert_allow "$out" 'absent Step 4 terminal sentinel foreground probe allows'
out=$(run_payload "$(payload_bash "$step4_foreground_probe" "$D")")
assert_allow "$out" 'Step 4 foreground probe allows second absent attempt'
out=$(run_payload "$(payload_bash "$step4_foreground_probe" "$D")")
assert_deny "$out" 'Step 4 foreground probe clamps repeated absent probes' "$EXPECTED_STEP"
non_step4_probe='[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$non_step4_probe" "$D")")
assert_deny "$out" 'design-step4-tail denies non-Step-4 foreground terminal probe' "$EXPECTED_STEP"
ordinary_step4_probe='test -f "$DESIGN_TMPDIR/.completed/step-4" && cat "$DESIGN_TMPDIR/rejected-findings.md"'
out=$(run_payload "$(payload_bash "$ordinary_step4_probe" "$D")")
assert_deny "$out" 'Step 4 foreground probe with appended read denies' "$EXPECTED_STEP"
rm -f "$D/.completed/step-4" "$D"/bg-poll-guard-probe-denials.*.count "$MARKER"

# #5925/#6080/#6108: cross-session false-positive regression. A live marker
# belonging to an unrelated repo clone must not deny a bare
# $IMPLEMENT_TMPDIR/$DESIGN_TMPDIR reference, direct foreign marker-dir reads,
# Monitor/TaskOutput, waiter, task-output, or probe-clamp paths issued from a
# DIFFERENT clone's cwd. A marker whose identity matches this cwd must still
# deny, including when the cwd is a subdirectory of the repo root.
CWD_OWN="$TMP/larch-owner-clone"
CWD_OWN_SUB="$CWD_OWN/sub/dir"
CWD_FOREIGN="$TMP/larch-foreign-clone"
mkdir -p "$CWD_OWN_SUB" "$CWD_FOREIGN"
D_OWN="$SESSIONS/claude-implement-larch-owner-clone-abcd1234"
D_UNRELATED="$SESSIONS/claude-design-larch-other-clone-zzzz9999"
mkdir -p "$D_OWN/.completed" "$D_OWN/plan-review" "$D_UNRELATED/.completed" "$D_UNRELATED/plan-review"
: >"$D_OWN/plan-review/ballot.txt"
: >"$D_UNRELATED/plan-review/ballot.txt"
MARKER_OWN="$D_OWN/.bg-wait-active"
MARKER_UNRELATED="$D_UNRELATED/.bg-wait-active"
write_keepalive "$D_OWN" "$CWD_OWN"
write_keepalive "$D_UNRELATED" "$CWD_FOREIGN"
implement_probe_bare='ls "$IMPLEMENT_TMPDIR"'
foreign_dir_probe="ls \"$D_UNRELATED\""
foreign_waiter='until [ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]; do sleep 30; done'
probe_clamp_foreign='[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo DONE || echo WAIT'

rm -f "$D_UNRELATED/bg-poll-guard-denials.count" "$D_UNRELATED"/bg-poll-guard-probe-denials.*.count
write_marker_at "$MARKER_UNRELATED" $$ "$(date +%s)" 21600 design-step3-review
out=$(run_payload_auto_markers "$(payload_bash "$implement_probe_bare" "$CWD_OWN")")
assert_allow "$out" '#5925: unrelated-clone live marker does not deny bare IMPLEMENT_TMPDIR reference from a different clone cwd'
out=$(run_payload_auto_markers "$(payload_bash "$foreign_dir_probe" "$CWD_OWN")")
assert_allow "$out" '#6108: known-foreign live marker does not deny Bash containing the foreign marker dir path'
out=$(run_payload_auto_markers "$(payload_read "$D_UNRELATED/plan-review/ballot.txt" "$CWD_OWN")")
assert_allow "$out" '#6108: known-foreign live marker does not deny Read under the foreign marker dir'
out=$(run_payload_auto_markers "$(payload_monitor "$CWD_OWN")")
assert_allow "$out" '#5925 follow-up: unrelated-clone live marker does not deny Monitor from a different clone cwd'
out=$(run_payload_auto_markers "$(payload_taskoutput "$CWD_OWN")")
assert_allow "$out" '#5925 follow-up: unrelated-clone live marker does not deny TaskOutput from a different clone cwd'
out=$(run_payload_auto_markers "$(payload_read 'tasks/foo.output' "$CWD_OWN")")
assert_allow "$out" '#5925 follow-up: unrelated-clone live marker does not deny own tasks/*.output Read from a different clone cwd'
out=$(run_payload_auto_markers "$(payload_bash 'cat tasks/foo.output' "$CWD_OWN")")
assert_allow "$out" '#6080: unrelated-clone live marker does not deny own tasks/*.output Bash read from a different clone cwd'
out=$(run_payload_auto_markers "$(payload_bash "$foreign_waiter" "$CWD_OWN")")
assert_allow "$out" '#6108: known-foreign live marker does not deny the Step 3 recovery waiter shape'
out=$(run_payload_auto_markers "$(payload_bash "$probe_clamp_foreign" "$CWD_OWN")")
assert_allow "$out" '#6108: known-foreign sole live marker does not bind foreground probe clamp'
if [ ! -e "$D_UNRELATED/bg-poll-guard-denials.count" ]; then
  pass '#6108: known-foreign live marker receives no denial telemetry from another clone'
else
  fail '#6108: known-foreign live marker must not receive denial telemetry from another clone'
fi
if [ ! -e "$D_UNRELATED/bg-poll-guard-probe-denials.step-3-terminal.count" ]; then
  pass '#6108: known-foreign sole live marker receives no probe-clamp telemetry from another clone'
else
  fail '#6108: known-foreign sole live marker must not receive probe-clamp telemetry from another clone'
fi
rm -f "$MARKER_UNRELATED"

write_marker_at "$MARKER_UNRELATED" $$ "$(date +%s)" 21600 design-step3-review
printf 'CLONE_PATH=%s\n' "$CWD_FOREIGN" >>"$MARKER_UNRELATED"
write_keepalive "$D_UNRELATED" "$CWD_OWN"
out=$(run_payload_auto_markers "$(payload_monitor "$CWD_OWN")")
assert_allow "$out" '#6138: marker-local foreign CLONE_PATH wins over same-clone keepalive for Monitor'
rm -f "$MARKER_UNRELATED"
write_keepalive "$D_UNRELATED" "$CWD_FOREIGN"

write_marker_at "$MARKER_OWN" $$ "$(date +%s)" 21600 implement-step5-review
printf 'CLONE_PATH=%s\n' "$CWD_OWN" >>"$MARKER_OWN"
write_keepalive "$D_OWN" "$CWD_FOREIGN"
out=$(run_payload_auto_markers "$(payload_monitor "$CWD_OWN")")
assert_deny "$out" '#6138: marker-local same-clone CLONE_PATH wins over foreign keepalive for Monitor' "$EXPECTED_STEP"
write_keepalive "$D_OWN" "$CWD_OWN"
out=$(run_payload_auto_markers "$(payload_bash "$implement_probe_bare" "$CWD_OWN")")
assert_deny "$out" '#5925: same-clone live marker still denies bare IMPLEMENT_TMPDIR reference from its own repo cwd' "$EXPECTED_STEP"
out=$(run_payload_auto_markers "$(payload_bash "\"$D_OWN\"" "$CWD_OWN")")
assert_deny "$out" '#6137: same-clone bare live marker dir Bash command denies' "$EXPECTED_STEP"
case "$D_OWN" in
  /private/*) D_OWN_ALIAS="${D_OWN#/private}" ;;
  *) D_OWN_ALIAS="/private$D_OWN" ;;
esac
out=$(run_payload_auto_markers "$(payload_bash "\"$D_OWN_ALIAS\"" "$CWD_OWN")")
assert_deny "$out" '#6137: same-clone bare live marker dir Bash command denies through /private alias' "$EXPECTED_STEP"
out=$(run_payload_auto_markers "$(payload_monitor "$CWD_OWN_SUB")")
assert_deny "$out" '#6108: same-clone keepalive still denies Monitor from a repo subdirectory cwd' "$EXPECTED_STEP"
out=$(run_payload_auto_markers "$(payload_taskoutput "$CWD_OWN_SUB")")
assert_deny "$out" '#6108: same-clone keepalive still denies TaskOutput from a repo subdirectory cwd' "$EXPECTED_STEP"
out=$(run_payload_auto_markers "$(payload_read 'tasks/foo.output' "$CWD_OWN_SUB")")
assert_allow "$out" '#6108: same-clone keepalive allows tasks/*.output Read classification from a repo subdirectory cwd'
out=$(run_payload_auto_markers "$(payload_bash 'cat tasks/foo.output' "$CWD_OWN_SUB")")
assert_deny "$out" '#6108: same-clone keepalive still denies tasks/*.output Bash from a repo subdirectory cwd' "$EXPECTED_STEP"
out=$(run_payload_auto_markers "$(payload_read "$D_OWN/plan-review/ballot.txt" "$CWD_OWN")")
assert_deny "$out" '#6108: same-clone Read under live marker dir still denies' "$EXPECTED_STEP"
out=$(run_payload_auto_markers "$(payload_read "$MARKER_OWN" "$CWD_OWN")")
assert_allow "$out" '#6108: same-clone Read of .bg-wait-active diagnosis marker allows'
out=$(run_payload_auto_markers "$(payload_bash "cat \"$MARKER_OWN\"" "$CWD_OWN")")
assert_allow "$out" '#6108: same-clone simple Bash read of .bg-wait-active diagnosis marker allows'
out=$(run_payload_with_marker "$MARKER_OWN" "$(payload_bash "awk '{print}' \"$MARKER_OWN\"" "$CWD_OWN")")
assert_allow "$out" '#6108: same-clone awk read of .bg-wait-active diagnosis marker allows'
out=$(run_payload_with_marker "$MARKER_OWN" "$(payload_bash "cat \"$MARKER_OWN\" # \"$D_OWN/plan-review/ballot.txt\"" "$CWD_OWN")")
assert_allow "$out" '#6108: comment-suffix .bg-wait-active diagnosis still allows after stripping comments'
out=$(run_payload_auto_markers "$(payload_bash "cat \"$MARKER_OWN\" && cat tasks/foo.output" "$CWD_OWN")")
assert_deny "$out" '#6108: mixed marker diagnosis plus progress artifact still denies' "$EXPECTED_STEP"
rm -f "$MARKER_OWN"

write_marker_at "$MARKER_OWN" $$ "$(date +%s)" 21600 implement-step5-review
write_keepalive "$D_OWN" "$CWD_OWN"
out=$(run_payload_auto_markers "$(payload_monitor "$CWD_OWN_SUB")")
assert_deny "$out" '#6138: marker without CLONE_PATH falls back to keepalive clone identity' "$EXPECTED_STEP"
rm -f "$D_OWN/.larch-keepalive"
out=$(run_payload_auto_markers "$(payload_bash "\"$D_OWN\"" "$CWD_FOREIGN")")
assert_deny "$out" '#6138: missing marker and keepalive identity still fails safe for direct marker-dir probe' "$EXPECTED_STEP"
rm -f "$MARKER_OWN"

# Hyphenated clone tags must still correlate correctly when keepalive identity is
# unavailable: the tag segment may itself contain "-", so parsing must not split
# naively on every hyphen.
CWD_HYPHEN="$TMP/my-repo-clone"
mkdir -p "$CWD_HYPHEN"
D_HYPHEN="$SESSIONS/claude-implement-my-repo-clone-wxyz7890"
mkdir -p "$D_HYPHEN/.completed"
MARKER_HYPHEN="$D_HYPHEN/.bg-wait-active"
write_marker_at "$MARKER_HYPHEN" $$ "$(date +%s)" 21600 implement-step5-review
out=$(run_payload_auto_markers "$(payload_bash "$implement_probe_bare" "$CWD_HYPHEN")")
assert_deny "$out" '#5925: hyphenated clone tag fallback still correlates and denies from its own repo cwd' "$EXPECTED_STEP"
rm -f "$MARKER_HYPHEN"

# The DESIGN_TMPDIR shape (not just IMPLEMENT_TMPDIR) must still deny from its
# own repo clone's cwd.
CWD_DESIGN_OWN="$TMP/larch-design-clone"
mkdir -p "$CWD_DESIGN_OWN"
D_DESIGN_OWN="$SESSIONS/claude-design-larch-design-clone-mnop4567"
mkdir -p "$D_DESIGN_OWN/.completed"
MARKER_DESIGN_OWN="$D_DESIGN_OWN/.bg-wait-active"
write_keepalive "$D_DESIGN_OWN" "$CWD_DESIGN_OWN"
write_marker_at "$MARKER_DESIGN_OWN" $$ "$(date +%s)" 21600 design-step3-review
out=$(run_payload_auto_markers "$(payload_bash "$design_tmpdir_ls" "$CWD_DESIGN_OWN")")
assert_deny "$out" '#5925: same-clone live design marker denies bare DESIGN_TMPDIR reference from its own repo cwd' "$EXPECTED_STEP"
rm -f "$MARKER_DESIGN_OWN"

# Missing/empty cwd cannot establish plausibility for the bare-reference match
# (no cwd-equals-dir signal, no clone tag to compare), so it fails open rather
# than denying — consistent with this hook's documented fail-open-on-uncertain
# input posture.
write_marker $$ "$(date +%s)" 21600 implement-step5-review
out=$(printf '%s' "$(jq -cn --arg cmd "$implement_probe_bare" '{tool_name:"Bash",tool_input:{command:$cmd},cwd:""}')" | LARCH_BG_POLL_GUARD_MARKER="$MARKER" "$HOOK")
assert_allow "$out" '#5925: empty cwd cannot establish plausibility, bare IMPLEMENT_TMPDIR reference allows'
rm -f "$MARKER"

# No marker: Monitor and TaskOutput are allowed.
rm -f "$MARKER"
out=$(run_payload "$(payload_monitor)")
assert_allow "$out" 'no marker allows Monitor'
out=$(run_payload "$(payload_taskoutput)")
assert_allow "$out" 'no marker allows TaskOutput'

if [ "$FAIL" -ne 0 ]; then
  printf 'FAIL: test-hook-bg-poll-guard.sh (%s failures, %s passes)\n' "$FAIL" "$PASS" >&2
  exit 1
fi
printf 'PASS: test-hook-bg-poll-guard.sh (%s checks)\n' "$PASS"
