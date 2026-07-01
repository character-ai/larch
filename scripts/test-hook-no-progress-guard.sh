#!/usr/bin/env bash
# test-hook-no-progress-guard.sh — offline harness for hook-no-progress-guard.sh.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HOOK="$SCRIPT_DIR/hook-no-progress-guard.sh"

[ -x "$HOOK" ] || { echo "FAIL: $HOOK not executable" >&2; exit 1; }

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }

TMP="$(mktemp -d "${TMPDIR:-/tmp}/test-hook-no-progress-guard.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
export TMPDIR="$TMP"
export HOME="$TMP/home"
mkdir -p "$HOME"

D="$TMP/larch-test-session"
mkdir -p "$D/.completed"
MARKER="$D/.bg-wait-active"

write_marker() {
  local pid="$1" start="${2:-$(date +%s)}" timeout="${3:-21600}" step="${4:-implement-step3-checks}"
  cat >"$MARKER" <<EOF_MARKER
PID=$pid
CLAUDE_PID=$$
START_EPOCH=$start
STEP=$step
TIMEOUT_S=$timeout
EOF_MARKER
}

stop_event() {
  printf '{"stop_hook_active":false,"cwd":"%s"}' "$D"
}

prompt_event() {
  printf '{"prompt":"some prompt","cwd":"%s"}' "$D"
}

# --- Helper: invoke hook with given event, return stdout ---
run_hook() {
  local input="$1"
  printf '%s' "$input" | \
    LARCH_BG_POLL_GUARD_MARKER="$MARKER" \
    LARCH_BG_POLL_GUARD_SESSION_PID=$$ \
    "$HOOK"
}

# --- T1: Stop event with no live marker → no counter file, no output ---
rm -f "$MARKER"
out=$(run_hook "$(stop_event)")
if [ -z "$out" ] && [ ! -f "$D/no-progress-turns.count" ]; then
  pass "T1: Stop with no marker → no counter, no output"
else
  fail "T1: Stop with no marker: out='$out' counter_exists=$(test -f "$D/no-progress-turns.count" && echo yes || echo no)"
fi

# --- T2: Stop event with live marker → counter increments ---
write_marker $$ "$(( $(date +%s) - 10 ))"
out=$(run_hook "$(stop_event)")
cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
  pass "T2: Stop with live marker → counter=1, no output"
else
  fail "T2: Stop with live marker: out='$out' cnt=$cnt"
fi

# --- T3: Multiple Stop events → counter increments ---
run_hook "$(stop_event)" >/dev/null
run_hook "$(stop_event)" >/dev/null
cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
if [ "$cnt" -eq 3 ]; then
  pass "T3: Three Stop events → counter=3"
else
  fail "T3: counter expected 3, got $cnt"
fi

# --- T4: Stop at threshold → breaker armed ---
THRESHOLD_VAL=5
while [ "$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)" -lt "$THRESHOLD_VAL" ]; do
  LARCH_BG_POLL_GUARD_MARKER="$MARKER" \
  LARCH_BG_POLL_GUARD_SESSION_PID=$$ \
  LARCH_NO_PROGRESS_GUARD_THRESHOLD=$THRESHOLD_VAL \
    "$HOOK" < <(stop_event) >/dev/null
done
if [ -f "$D/no-progress-circuit-breaker-armed" ]; then
  pass "T4: breaker armed after threshold=$THRESHOLD_VAL Stop events"
else
  fail "T4: breaker not armed after threshold=$THRESHOLD_VAL Stop events"
fi

# --- T5: UserPromptSubmit with armed breaker → blocked ---
out=$(LARCH_BG_POLL_GUARD_MARKER="$MARKER" LARCH_BG_POLL_GUARD_SESSION_PID=$$ run_hook "$(prompt_event)")
case "$out" in
  *'"decision":"block"'*) pass "T5: UserPromptSubmit with armed breaker → blocked" ;;
  *) fail "T5: UserPromptSubmit with armed breaker: out='$out'" ;;
esac

# --- T6: UserPromptSubmit without armed breaker → allowed ---
rm -f "$D/no-progress-circuit-breaker-armed" "$D/no-progress-turns.count"
write_marker $$
out=$(LARCH_BG_POLL_GUARD_MARKER="$MARKER" LARCH_BG_POLL_GUARD_SESSION_PID=$$ run_hook "$(prompt_event)")
if [ -z "$out" ]; then
  pass "T6: UserPromptSubmit without armed breaker → allowed"
else
  fail "T6: unexpected block: out='$out'"
fi

# --- T7: Step terminal sentinel present → not live, no count ---
rm -f "$D/no-progress-turns.count" "$D/no-progress-circuit-breaker-armed"
write_marker $$ "$(( $(date +%s) - 10 ))" 21600 implement-step3-checks
touch "$D/.completed/step-3-terminal"
out=$(run_hook "$(stop_event)")
cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 0 ]; then
  pass "T7: terminal sentinel present → marker not live, counter not incremented"
else
  fail "T7: expected no count with sentinel: out='$out' cnt=$cnt"
fi

# --- T8: DISABLE env var → no action ---
rm -f "$D/.completed/step-3-terminal" "$D/no-progress-turns.count"
write_marker $$
out=$(LARCH_BG_POLL_GUARD_MARKER="$MARKER" LARCH_NO_PROGRESS_GUARD_DISABLE=1 run_hook "$(stop_event)")
cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 0 ]; then
  pass "T8: DISABLE=1 → hook no-ops"
else
  fail "T8: disable failed: out='$out' cnt=$cnt"
fi

# --- T9: Stop re-entry guard (stop_hook_active=true) → no count ---
rm -f "$D/no-progress-turns.count"
write_marker $$
out=$(printf '{"stop_hook_active":true,"cwd":"%s"}' "$D" | \
  LARCH_BG_POLL_GUARD_MARKER="$MARKER" LARCH_BG_POLL_GUARD_SESSION_PID=$$ "$HOOK")
cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 0 ]; then
  pass "T9: stop_hook_active=true → re-entry guard, no count"
else
  fail "T9: re-entry guard failed: out='$out' cnt=$cnt"
fi

# --- T10: Custom threshold via env var ---
rm -f "$D/no-progress-turns.count" "$D/no-progress-circuit-breaker-armed"
write_marker $$
# Threshold=2: armed after 2 Stop events
for _ in 1 2; do
  LARCH_BG_POLL_GUARD_MARKER="$MARKER" \
  LARCH_BG_POLL_GUARD_SESSION_PID=$$ \
  LARCH_NO_PROGRESS_GUARD_THRESHOLD=2 \
    "$HOOK" < <(stop_event) >/dev/null
done
if [ -f "$D/no-progress-circuit-breaker-armed" ]; then
  pass "T10: custom threshold=2 → breaker armed after 2 Stop events"
else
  fail "T10: custom threshold=2 but breaker not armed"
fi

# --- T11: Step 3 sentinel without persist sidecar → marker still live, counter increments ---
rm -f "$D/no-progress-turns.count" "$D/no-progress-circuit-breaker-armed" "$MARKER"
write_marker $$ "$(( $(date +%s) - 10 ))" 21600 design-step3-review
: >"$D/.completed/step-3-terminal"
rm -f "$D/.step3-terminal-persisted-this-run"
out=$(run_hook "$(stop_event)")
cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
  pass "T11: step3 sentinel without sidecar → marker still live, counter increments"
else
  fail "T11: expected count=1 with stale sentinel: out='$out' cnt=$cnt"
fi
rm -f "$D/.completed/step-3-terminal" "$MARKER"

# --- T12: stale breaker clears on dead PID; fresh marker in same tmpdir is not blocked ---
write_marker $$ "$(( $(date +%s) - 10 ))" 21600 implement-step3-checks
THRESHOLD_VAL=2
while [ "$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)" -lt "$THRESHOLD_VAL" ]; do
  LARCH_BG_POLL_GUARD_MARKER="$MARKER" \
  LARCH_BG_POLL_GUARD_SESSION_PID=$$ \
  LARCH_NO_PROGRESS_GUARD_THRESHOLD=$THRESHOLD_VAL \
    "$HOOK" < <(stop_event) >/dev/null
done
[ -f "$D/no-progress-circuit-breaker-armed" ] || fail "T12: pre-relaunch breaker not armed"
write_marker 999999 "$(date +%s)" 21600 implement-step3-checks
run_hook "$(stop_event)" >/dev/null
if [ -f "$D/no-progress-circuit-breaker-armed" ]; then
  fail "T12: dead PID must clear armed breaker"
else
  pass "T12: dead PID clears armed breaker"
fi
write_marker $$ "$(( $(date +%s) - 10 ))" 21600 implement-step5-review
out=$(LARCH_BG_POLL_GUARD_MARKER="$MARKER" LARCH_BG_POLL_GUARD_SESSION_PID=$$ run_hook "$(prompt_event)")
if [ -z "$out" ]; then
  pass "T12: fresh marker after dead removal → UserPromptSubmit allowed"
else
  fail "T12: fresh marker blocked by stale armed state: out='$out'"
fi
rm -f "$MARKER"

# --- T13: sequential wait relaunch clears counter on new marker write path via dead PID reap ---
write_marker $$ "$(( $(date +%s) - 10 ))" 21600 implement-step3-checks
for _ in 1 2 3; do run_hook "$(stop_event)" >/dev/null; done
cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
write_marker 999999 "$(date +%s)" 21600 implement-step3-checks
run_hook "$(stop_event)" >/dev/null
write_marker $$ "$(( $(date +%s) - 10 ))" 21600 implement-step5-review
run_hook "$(stop_event)" >/dev/null
cnt2=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
if [ "$cnt2" -eq 1 ]; then
  pass "T13: relaunched wait starts with fresh counter (cnt=$cnt before, cnt2=$cnt2)"
else
  fail "T13: expected counter=1 after relaunch, got cnt=$cnt before cnt2=$cnt2"
fi
rm -f "$MARKER"

# --- T14: #5684 production-divergence, foreign CLAUDE_PID, no session-PID env → still live, counter increments ---
# In production the hook's PPID/input never match the marker's stored CLAUDE_PID and
# LARCH_BG_POLL_GUARD_SESSION_PID is unset, so the old equality check skipped every marker
# and the breaker never armed. A live marker must now count regardless of stored CLAUDE_PID.
rm -f "$D/no-progress-turns.count" "$D/no-progress-circuit-breaker-armed" "$MARKER"
printf '%s\n' "PID=$$" "CLAUDE_PID=999999999" "START_EPOCH=$(( $(date +%s) - 10 ))" "STEP=implement-step3-checks" "TIMEOUT_S=21600" >"$MARKER"
out=$(printf '%s' "$(stop_event)" | LARCH_BG_POLL_GUARD_MARKER="$MARKER" "$HOOK")
cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
  pass "T14: foreign CLAUDE_PID without session-PID env → marker live, counter increments (#5684)"
else
  fail "T14: expected count=1 for foreign-CLAUDE_PID live marker: out='$out' cnt=$cnt"
fi
rm -f "$MARKER"

# --- T15: Step 8 marker counts and rc sidecar releases; symlink rc does not complete ---
rm -f "$D/no-progress-turns.count" "$D/no-progress-circuit-breaker-armed" "$D/.step-8-ship-handoff.rc" "$MARKER"
write_marker $$ "$(( $(date +%s) - 10 ))" 21600 implement-step8-ship
out=$(run_hook "$(stop_event)")
cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
  pass "T15: Step 8 live marker increments no-progress counter"
else
  fail "T15: expected Step 8 count=1: out='$out' cnt=$cnt"
fi
LARCH_BG_POLL_GUARD_MARKER="$MARKER" \
LARCH_BG_POLL_GUARD_SESSION_PID=$$ \
LARCH_NO_PROGRESS_GUARD_THRESHOLD=2 \
  "$HOOK" < <(stop_event) >/dev/null
if [ -f "$D/no-progress-circuit-breaker-armed" ]; then
  pass "T15: Step 8 breaker arms at low threshold"
else
  fail "T15: Step 8 breaker did not arm"
fi
out=$(LARCH_BG_POLL_GUARD_MARKER="$MARKER" LARCH_BG_POLL_GUARD_SESSION_PID=$$ run_hook "$(prompt_event)")
case "$out" in
  *'"decision":"block"'*) pass "T15: Step 8 armed breaker blocks UserPromptSubmit" ;;
  *) fail "T15: Step 8 armed breaker expected block: out='$out'" ;;
esac
: >"$D/.step-8-ship-handoff.rc"
out=$(LARCH_BG_POLL_GUARD_MARKER="$MARKER" LARCH_BG_POLL_GUARD_SESSION_PID=$$ run_hook "$(prompt_event)")
if [ -z "$out" ] && [ ! -f "$D/no-progress-circuit-breaker-armed" ]; then
  pass "T15: Step 8 rc sidecar auto-disarms and allows prompt"
else
  fail "T15: Step 8 rc sidecar should disarm: out='$out' armed=$(test -f "$D/no-progress-circuit-breaker-armed" && echo yes || echo no)"
fi
rm -f "$D/.step-8-ship-handoff.rc" "$D/no-progress-turns.count" "$D/no-progress-circuit-breaker-armed"
: >"$D/.step-8-real-rc"
ln -s "$D/.step-8-real-rc" "$D/.step-8-ship-handoff.rc"
write_marker $$ "$(( $(date +%s) - 10 ))" 21600 implement-step8-ship
out=$(run_hook "$(stop_event)")
cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
  pass "T15: symlinked Step 8 rc sidecar does not count as completion"
else
  fail "T15: symlinked Step 8 rc expected live marker: out='$out' cnt=$cnt"
fi
rm -f "$D/.step-8-ship-handoff.rc" "$D/.step-8-real-rc" "$MARKER"

for spec in \
  'design-step4-tail:.completed/step-4' \
  'implement-step7a:.completed/step-7a-terminal' \
  'implement-step6-checks:.completed/step-6-terminal' \
  'implement-step5-resume:.completed/step-5-resume-terminal' \
  'implement-step5-self-review:.completed/step-5-self-review-terminal'
do
  step=${spec%%:*}
  sentinel=${spec#*:}
  rm -f "$D/no-progress-turns.count" "$D/no-progress-circuit-breaker-armed" "$MARKER" "$D/.completed/"*
  mkdir -p "$D/.completed"
  write_marker $$ "$(( $(date +%s) - 10 ))" 21600 "$step"
  out=$(run_hook "$(stop_event)")
  cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
  if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
    pass "new marker coverage: $step increments no-progress counter"
  else
    fail "new marker coverage: expected $step count=1: out='$out' cnt=$cnt"
  fi
  LARCH_BG_POLL_GUARD_MARKER="$MARKER" \
  LARCH_BG_POLL_GUARD_SESSION_PID=$$ \
  LARCH_NO_PROGRESS_GUARD_THRESHOLD=2 \
    "$HOOK" < <(stop_event) >/dev/null
  if [ -f "$D/no-progress-circuit-breaker-armed" ]; then
    pass "new marker coverage: $step breaker arms at low threshold"
  else
    fail "new marker coverage: $step breaker did not arm"
  fi
  : >"$D/$sentinel"
  out=$(LARCH_BG_POLL_GUARD_MARKER="$MARKER" LARCH_BG_POLL_GUARD_SESSION_PID=$$ run_hook "$(prompt_event)")
  if [ -z "$out" ] && [ ! -f "$D/no-progress-circuit-breaker-armed" ]; then
    pass "new marker coverage: $step terminal sentinel clears breaker"
  else
    fail "new marker coverage: $step terminal sentinel should clear: out='$out' armed=$(test -f "$D/no-progress-circuit-breaker-armed" && echo yes || echo no)"
  fi
  rm -f "$D/no-progress-turns.count" "$D/no-progress-circuit-breaker-armed" "$D/$sentinel"
  : >"$D/.completed/real-target"
  ln -s "$D/.completed/real-target" "$D/$sentinel"
  write_marker $$ "$(( $(date +%s) - 10 ))" 21600 "$step"
  out=$(run_hook "$(stop_event)")
  cnt=$(cat "$D/no-progress-turns.count" 2>/dev/null || echo 0)
  if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
    pass "new marker coverage: symlinked $step sentinel does not complete wait"
  else
    fail "new marker coverage: symlinked $step sentinel expected live marker: out='$out' cnt=$cnt"
  fi
  rm -f "$D/$sentinel" "$D/.completed/real-target" "$D/no-progress-turns.count" "$MARKER"
done

# --- T16: TMPDIR claude-implement-* fallback discovery without marker override ---
D_IMPL="$TMP/claude-implement-fallback-xyz"
mkdir -p "$D_IMPL"
MARKER_IMPL="$D_IMPL/.bg-wait-active"
printf '%s\n' "PID=$$" "CLAUDE_PID=$$" "START_EPOCH=$(( $(date +%s) - 10 ))" "STEP=implement-step3-checks" "TIMEOUT_S=21600" >"$MARKER_IMPL"
rm -f "$D_IMPL/no-progress-turns.count"
out=$(printf '{"stop_hook_active":false,"cwd":"%s"}' "$D_IMPL" | "$HOOK")
cnt=$(cat "$D_IMPL/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
  pass "T16: TMPDIR claude-implement-* fallback discovery without marker override"
else
  fail "T16: expected count=1 via TMPDIR fallback discovery: out='$out' cnt=$cnt"
fi
rm -f "$MARKER_IMPL"

# --- Summary ---
printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
