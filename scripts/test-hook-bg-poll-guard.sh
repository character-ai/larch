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

write_marker() {
  local pid="$1" start="$2" timeout="${3:-21600}" step="${4:-design-step3-review}"
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

run_payload() {
  local payload="$1"
  printf '%s' "$payload" | LARCH_BG_POLL_GUARD_MARKER="$MARKER" LARCH_BG_POLL_GUARD_SESSION_PID="${LARCH_BG_POLL_GUARD_SESSION_PID:-}" "$HOOK"
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
  local out="$1" label="$2"
  if printf '%s' "$out" | jq -e '.hookSpecificOutput.hookEventName == "PreToolUse" and .hookSpecificOutput.permissionDecision == "deny"' >/dev/null 2>&1; then
    pass "$label"
  else
    fail "$label (expected deny JSON, got: $out)"
  fi
  if printf '%s' "$out" | grep -Fq "$D"; then
    fail "$label deny reason must not echo raw tmpdir path"
  fi
}

if jq -e --arg cmd 'hook-bg-poll-guard.sh' '
    .hooks.PreToolUse[]?
    | select(.matcher == "Read|Bash")
    | .hooks[]?
    | select(.command | test($cmd))
' "$HOOKS_JSON" >/dev/null 2>&1; then
  pass 'hooks.json registers hook-bg-poll-guard.sh under PreToolUse Read|Bash'
else
  fail 'hooks.json must register hook-bg-poll-guard.sh under PreToolUse Read|Bash'
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
out=$(run_payload "$(payload_read "$D/plan-review/round-1/ballot.txt")")
assert_deny "$out" 'live marker plus Read under DESIGN_TMPDIR denies'

out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'live marker plus Bash ls DESIGN_TMPDIR denies'

session_tmpdir_ls="ls \"\$SESSION_TMPDIR\""
out=$(run_payload "$(payload_bash "$session_tmpdir_ls")")
assert_deny "$out" 'live marker plus Bash ls SESSION_TMPDIR denies'

out=$(run_payload "$(payload_bash 'cat .step3-review-result.env' "$D")")
assert_deny "$out" 'live marker plus cat result env in tmpdir context denies'

out=$(run_payload "$(payload_bash "sleep 30 && $design_tmpdir_ls")")
assert_deny "$out" 'live marker plus sleep N && probe denies'

watcher_cmd="while [ ! -f .step3-review-result.env ]; do sleep 5; $design_tmpdir_ls; done"
out=$(run_payload "$(payload_bash "$watcher_cmd")")
assert_deny "$out" 'live marker plus watcher loop denies'

out=$(run_payload "$(payload_read 'tasks/foo.output')")
assert_deny "$out" 'live marker plus Read tasks/foo.output denies'

out=$(run_payload "$(payload_bash "\"\$HOME/.cache/larch/sessions/design-run-123.sh\" design-step3-review.sh")")
assert_allow "$out" 'wrapper-routed design-run call allows'

compound_wrapper_probe="\"\$HOME/.cache/larch/sessions/design-run-123.sh\" design-step3-review.sh && $design_tmpdir_ls"
out=$(run_payload "$(payload_bash "$compound_wrapper_probe")")
assert_deny "$out" 'compound wrapper plus appended probe denies'

step3_recovery_waiter="until [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter" "$D")")
assert_allow "$out" 'exact Step 3 recovery waiter allows'

step3_recovery_waiter_braced="until [ -f \"\${DESIGN_TMPDIR}/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_braced" "$D")")
assert_allow "$out" 'braced Step 3 recovery waiter allows'

# #4489: a single leading DESIGN_TMPDIR=<abs>; assignment is accepted so the
# waiter resolves when the shell has not exported $DESIGN_TMPDIR.
step3_recovery_waiter_prefixed="DESIGN_TMPDIR=/tmp/larch-design-xyz; until [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_prefixed" "$D")")
assert_allow "$out" 'DESIGN_TMPDIR-prefixed Step 3 recovery waiter allows'

step3_recovery_waiter_prefixed_braced="DESIGN_TMPDIR=/tmp/larch-design-xyz; until [ -f \"\${DESIGN_TMPDIR}/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_prefixed_braced" "$D")")
assert_allow "$out" 'DESIGN_TMPDIR-prefixed braced Step 3 recovery waiter allows'

step3_recovery_waiter_prefixed_probe="DESIGN_TMPDIR=/tmp/larch-design-xyz; until [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ]; do sleep 30; done && cat \"\$DESIGN_TMPDIR/.step3-review-result.env\""
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_prefixed_probe" "$D")")
assert_deny "$out" 'DESIGN_TMPDIR-prefixed Step 3 recovery waiter with appended probe denies'

step3_recovery_waiter_probe="until [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ]; do sleep 30; done && cat \"\$DESIGN_TMPDIR/.step3-review-result.env\""
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_probe" "$D")")
assert_deny "$out" 'Step 3 recovery waiter with appended probe denies'

filetest_loop='while [ ! -f .step3-review-result.env ]; do sleep 5; done'
out=$(run_payload "$(payload_bash "$filetest_loop" "$D")")
assert_deny "$out" 'live marker plus file-test sleep loop denies'

step3_result_waiter="until [ -f \"\$DESIGN_TMPDIR/.step3-review-result.env\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_result_waiter" "$D")")
assert_deny "$out" 'Step 3 result-env waiter remains denied'

write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
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
assert_deny "$out" 'foreground probe of non-terminal Step 5c sentinel denies'

write_marker $$ "$(date +%s)" 21600 design-step3-review
nonterminal_step3_probe='test -f "${DESIGN_TMPDIR}/.completed/step-3" && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$nonterminal_step3_probe" "$D")")
assert_deny "$out" 'foreground probe of non-terminal Step 3 sentinel denies'

sentinel_probe_sleep='test -f "${DESIGN_TMPDIR}/.completed/step-3-terminal" && sleep 1'
out=$(run_payload "$(payload_bash "$sentinel_probe_sleep" "$D")")
assert_deny "$out" 'foreground terminal sentinel probe plus sleep denies'

sentinel_probe_until='until [ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]; do :; done'
out=$(run_payload "$(payload_bash "$sentinel_probe_until" "$D")")
assert_deny "$out" 'foreground terminal sentinel probe wrapped in until denies'

sentinel_probe_while='while [ ! -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]; do :; done'
out=$(run_payload "$(payload_bash "$sentinel_probe_while" "$D")")
assert_deny "$out" 'foreground terminal sentinel probe wrapped in while denies'

result_env_probe='test -f "$DESIGN_TMPDIR/.step3-review-result.env" && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$result_env_probe" "$D")")
assert_deny "$out" 'foreground probe of Step 3 result env denies'

publish_env_probe='test -f "$DESIGN_TMPDIR/.design-publish-result.env" && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$publish_env_probe" "$D")")
assert_deny "$out" 'foreground probe of publish result env denies'

for verb in cat ls stat jq; do
  appended_probe="test -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" && $verb \"\$DESIGN_TMPDIR/.step3-review-result.env\""
  out=$(run_payload "$(payload_bash "$appended_probe" "$D")")
  assert_deny "$out" "foreground terminal sentinel probe with appended $verb denies"
done

cmd_sub_probe='[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ] && echo DONE || echo $(cat "$DESIGN_TMPDIR/.step3-review-result.env")'
out=$(run_payload "$(payload_bash "$cmd_sub_probe" "$D")")
assert_deny "$out" 'foreground terminal sentinel probe with command substitution in echo tail denies'

informal_probe="DESIGN_TMPDIR=/tmp/informal-design; [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ] && echo DONE || echo WAIT"
out=$(run_payload "$(payload_bash "$informal_probe" "$D")")
assert_deny "$out" 'foreground probe with DESIGN_TMPDIR outside live marker dir denies'

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
assert_deny "$out" 'live marker plus touch of terminal sentinel denies'

mkdir -p "$D/.completed"
write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
: >"$D/.completed/real-terminal-target"
ln -s "$D/.completed/real-terminal-target" "$D/.completed/step-3-terminal"
out=$(run_payload "$(payload_bash "$terminal_probe_step3" "$D")")
assert_deny "$out" 'symlinked terminal sentinel foreground probe denies'
rm -f "$D/.completed/step-3-terminal"

write_marker $$ "$(date +%s)" 21600 design-step5c
: >"$D/.completed/step-5c"
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'Step 5c non-terminal sentinel does not release marker'
: >"$D/.completed/step-5c-terminal"
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'Step 5c terminal sentinel releases marker'
rm -f "$D/.completed/step-5c" "$D/.completed/step-5c-terminal"

out=$(run_payload "$(payload_bash "rg plan-review docs/" "/tmp/other-repo")")
assert_allow "$out" 'plan-review substring outside live tmpdir allows'

out=$(run_payload "$(payload_bash "awk '{print}' \"\$DESIGN_TMPDIR/plan-review/round-1/foo-output.txt\"")")
assert_deny "$out" 'live marker plus awk against DESIGN_TMPDIR output denies'

write_marker $$ "$(date +%s)"
printf '%s\n' "PID=$$" "CLAUDE_PID=999999999" "START_EPOCH=$(date +%s)" "STEP=design-step3-review" "TIMEOUT_S=21600" >"$MARKER"
out=$(LARCH_BG_POLL_GUARD_SESSION_PID=$$ run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'foreign-session marker does not deny current session'
write_marker $$ "$(date +%s)"
printf '0\n' >"$D/bg-poll-guard-denials.count"
chmod 444 "$D/bg-poll-guard-denials.count" 2>/dev/null || true
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
chmod 644 "$D/bg-poll-guard-denials.count" 2>/dev/null || true
assert_deny "$out" 'deny JSON emitted even when telemetry count write fails'

out=$(printf '{not-json' | LARCH_BG_POLL_GUARD_MARKER="$MARKER" "$HOOK")
assert_allow "$out" 'malformed JSON silently allows'

NOJQ="$TMP/nojq-bin"
mkdir -p "$NOJQ"
ln -s /bin/cat "$NOJQ/cat"
ln -s "$(command -v bash)" "$NOJQ/bash"
out=$(printf '%s' "$(payload_bash "$design_tmpdir_ls")" | PATH="$NOJQ" LARCH_BG_POLL_GUARD_MARKER="$MARKER" "$HOOK" 2>/dev/null || true)
assert_allow "$out" 'missing jq path silently allows'

out=$(run_payload "$(payload_bash 'grep foo final-summary.md' "$D")")
assert_deny "$out" 'deny JSON carries PreToolUse and permissionDecision=deny'

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
assert_deny "$out" 'step3 terminal sentinel without persist sidecar does not release marker'
rm -f "$D/.completed/step-3-terminal" "$MARKER"

write_marker $$ "$(date +%s)" 21600 design-step5c
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'step-3-terminal sentinel does not release a non-step3 marker'

write_marker $$ "$(date +%s)" 21600 design-step3-review
rm -f "$D/.completed/step-3-terminal"
: >"$D/.completed/real-target"
ln -s "$D/.completed/real-target" "$D/.completed/step-3-terminal"
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'symlinked completion sentinel does not release'
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

if [ "$FAIL" -ne 0 ]; then
  printf 'FAIL: test-hook-bg-poll-guard.sh (%s failures, %s passes)\n' "$FAIL" "$PASS" >&2
  exit 1
fi
printf 'PASS: test-hook-bg-poll-guard.sh (%s checks)\n' "$PASS"
