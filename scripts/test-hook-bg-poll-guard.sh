#!/usr/bin/env bash
# test-hook-bg-poll-guard.sh — offline harness for hook-bg-poll-guard.sh.
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
  printf '%s' "$payload" | LARCH_BG_POLL_GUARD_MARKER="$MARKER" "$HOOK"
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

if [ "$FAIL" -ne 0 ]; then
  printf 'FAIL: test-hook-bg-poll-guard.sh (%s failures, %s passes)\n' "$FAIL" "$PASS" >&2
  exit 1
fi
printf 'PASS: test-hook-bg-poll-guard.sh (%s checks)\n' "$PASS"
