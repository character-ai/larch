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

write_marker_at() {
  local marker="$1" pid="$2" start="$3" timeout="${4:-21600}" step="${5:-design-step3-review}"
  cat >"$marker" <<EOF_MARKER
PID=$pid
CLAUDE_PID=$$
START_EPOCH=$start
STEP=$step
TIMEOUT_S=$timeout
EOF_MARKER
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

# #4725: the bare background sleep-loop Step 3 recovery waiter is now DENIED (it
# used to be allowed). It is a zero-output background task that breeds its own
# premature notifications, so the guard forces the foreground, non-sleeping
# terminal-sentinel probe path instead.
step3_recovery_waiter="until [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter" "$D")")
assert_deny "$out" 'exact Step 3 recovery waiter denies'

step3_recovery_waiter_braced="until [ -f \"\${DESIGN_TMPDIR}/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_braced" "$D")")
assert_deny "$out" 'braced Step 3 recovery waiter denies'

# #4489 / #4725: a single leading DESIGN_TMPDIR=<abs>; assignment still matches the
# exact-waiter shape, so the prefixed waiter is denied too.
step3_recovery_waiter_prefixed="DESIGN_TMPDIR=/tmp/larch-design-xyz; until [ -f \"\$DESIGN_TMPDIR/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_prefixed" "$D")")
assert_deny "$out" 'DESIGN_TMPDIR-prefixed Step 3 recovery waiter denies'

step3_recovery_waiter_prefixed_braced="DESIGN_TMPDIR=/tmp/larch-design-xyz; until [ -f \"\${DESIGN_TMPDIR}/.completed/step-3-terminal\" ]; do sleep 30; done"
out=$(run_payload "$(payload_bash "$step3_recovery_waiter_prefixed_braced" "$D")")
assert_deny "$out" 'DESIGN_TMPDIR-prefixed braced Step 3 recovery waiter denies'

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
assert_deny "$out" 'foreground probe of non-terminal Step 5c sentinel denies'

write_marker $$ "$(date +%s)" 21600 design-step3-review
nonterminal_step3_probe='test -f "${DESIGN_TMPDIR}/.completed/step-3" && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$nonterminal_step3_probe" "$D")")
assert_deny "$out" 'foreground probe of non-terminal Step 3 sentinel denies'

write_marker $$ "$(date +%s)" 21600 design-step3-review
nonterminal_step35_probe='[[ -f "${DESIGN_TMPDIR}/.completed/step-3.5" ]] && echo DONE || echo WAIT'
out=$(run_payload "$(payload_bash "$nonterminal_step35_probe" "$D")")
assert_deny "$out" 'foreground probe of Step 3.5 sentinel denies'

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
assert_deny "$out" 'stale step-3 milestone without step-3-terminal does not release marker'
rm -f "$D/.completed/step-3"
write_marker $$ "$(date +%s)" 21600 design-step3-review

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
assert_deny "$out" 'compound tasks/output plus terminal-sentinel probe denies via generic path'

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
  assert_deny "$out" "live marker plus alternate sentinel forgery denies: $alt_forgery"
done

sidecar_forgery=': >"\$DESIGN_TMPDIR/.step3-terminal-persisted-this-run"'
out=$(run_payload "$(payload_bash "$sidecar_forgery" "$D")")
assert_deny "$out" 'live marker plus sidecar forgery denies'

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

# #5684: production-divergence regression. In production the hook's PPID/input never
# match the marker's stored CLAUDE_PID and LARCH_BG_POLL_GUARD_SESSION_PID is unset, so
# the old CLAUDE_PID equality check rejected every marker and the guard never fired. A
# live marker (alive PID, within age) must now deny regardless of the stored CLAUDE_PID,
# with no session-PID env set — exactly the real hook environment.
printf '%s\n' "PID=$$" "CLAUDE_PID=999999999" "START_EPOCH=$(date +%s)" "STEP=design-step3-review" "TIMEOUT_S=21600" >"$MARKER"
out=$(printf '%s' "$(payload_bash "$design_tmpdir_ls")" | LARCH_BG_POLL_GUARD_MARKER="$MARKER" "$HOOK")
assert_deny "$out" 'live marker denies regardless of stored CLAUDE_PID without session-PID env (#5684)'
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
assert_deny "$out" 'probe clamp: 3rd consecutive probe against absent sentinel denies'
out=$(run_payload "$(payload_bash "$probe_clamp_cmd" "$D")")
assert_deny "$out" 'probe clamp: stays denied while sentinel absent'

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
assert_deny "$out" 'probe clamp: threshold=1 denies 2nd probe'
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
assert_deny "$out" 'probe clamp: pre-relaunch 3rd probe denies'
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
assert_deny "$out" 'parallel clamp: dir A 3rd probe denies'
out=$(run_payload_auto_markers "$(payload_bash "$probe_clamp_b" "$D_B")")
assert_allow "$out" 'parallel clamp: dir B unaffected after dir A clamp tripped'
rm -f "$MARKER_A" "$MARKER_B" \
  "$D_A"/bg-poll-guard-probe-denials.*.count "$D_B"/bg-poll-guard-probe-denials.*.count

# Monitor and TaskOutput are always denied while any live marker is active.
write_marker $$ "$(date +%s)" 21600 design-step3-review
out=$(run_payload "$(payload_monitor)")
assert_deny "$out" 'live design marker plus Monitor denies'

out=$(run_payload "$(payload_taskoutput)")
assert_deny "$out" 'live design marker plus TaskOutput denies'

# Implement bg-wait markers: implement-step3-checks and implement-step5-review.
write_marker $$ "$(date +%s)" 21600 implement-step3-checks
out=$(run_payload "$(payload_monitor)")
assert_deny "$out" 'live implement-step3-checks marker plus Monitor denies'

out=$(run_payload "$(payload_taskoutput)")
assert_deny "$out" 'live implement-step3-checks marker plus TaskOutput denies'

out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_deny "$out" 'live implement-step3-checks marker denies Bash probe'

# implement-step3-checks terminal sentinel releases the marker.
mkdir -p "$D/.completed"
write_marker $$ "$(date +%s)" 21600 implement-step3-checks
: >"$D/.completed/step-3-terminal"
out=$(run_payload "$(payload_monitor)")
assert_allow "$out" 'implement-step3-checks step-3-terminal sentinel releases Monitor'
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'implement-step3-checks step-3-terminal sentinel releases Bash probe'
rm -f "$D/.completed/step-3-terminal" "$MARKER"

# implement-step5-review marker and terminal sentinel.
write_marker $$ "$(date +%s)" 21600 implement-step5-review
out=$(run_payload "$(payload_monitor)")
assert_deny "$out" 'live implement-step5-review marker plus Monitor denies'

out=$(run_payload "$(payload_taskoutput)")
assert_deny "$out" 'live implement-step5-review marker plus TaskOutput denies'

# IMPLEMENT_TMPDIR reference in Bash probe is denied when implement marker is live.
implement_probe='ls "$IMPLEMENT_TMPDIR"'
out=$(run_payload "$(payload_bash "$implement_probe")")
assert_deny "$out" 'live implement-step5-review marker plus Bash ls IMPLEMENT_TMPDIR denies'

# implement-step5-review terminal sentinel releases the marker.
write_marker $$ "$(date +%s)" 21600 implement-step5-review
: >"$D/.completed/step-5-terminal"
out=$(run_payload "$(payload_monitor)")
assert_allow "$out" 'implement-step5-review step-5-terminal sentinel releases Monitor'
out=$(run_payload "$(payload_bash "$design_tmpdir_ls")")
assert_allow "$out" 'implement-step5-review step-5-terminal sentinel releases Bash probe'
rm -f "$D/.completed/step-5-terminal" "$MARKER"

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
