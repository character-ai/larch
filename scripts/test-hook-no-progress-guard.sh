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

write_keepalive() {
  local dir="$1" clone_path="$2"
  printf 'CLONE_PATH=%s\n' "$clone_path" >"$dir/.larch-keepalive"
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

# --- T17: clone-scoped blocking — two markers with distinct CLONE_PATH identities (#5927) ---
# MA belongs to clone-a, MB belongs to clone-b. Each is armed. A UserPromptSubmit whose cwd
# matches a marker's own recorded clone is still blocked (owning session); a UserPromptSubmit
# whose cwd matches the OTHER clone is not blocked by that foreign marker.
D_A="$TMP/claude-design-clonea-marker"
D_B="$TMP/claude-implement-cloneb-marker"
mkdir -p "$D_A" "$D_B"
CLONE_A="$TMP/clone-a-repo"
CLONE_B="$TMP/clone-b-repo"
mkdir -p "$CLONE_A" "$CLONE_B"
MARKER_A="$D_A/.bg-wait-active"
MARKER_B="$D_B/.bg-wait-active"
printf '%s\n' "PID=$$" "CLAUDE_PID=$$" "START_EPOCH=$(( $(date +%s) - 10 ))" "STEP=design-step3-review" "TIMEOUT_S=21600" >"$MARKER_A"
printf 'CLONE_PATH=%s\nSESSION_ID=test-clone-a\n' "$CLONE_A" >"$D_A/.larch-keepalive"
printf '%s\n' "PID=$$" "CLAUDE_PID=$$" "START_EPOCH=$(( $(date +%s) - 10 ))" "STEP=implement-step3-checks" "TIMEOUT_S=21600" >"$MARKER_B"
printf 'CLONE_PATH=%s\nSESSION_ID=test-clone-b\n' "$CLONE_B" >"$D_B/.larch-keepalive"
touch "$D_A/no-progress-circuit-breaker-armed" "$D_B/no-progress-circuit-breaker-armed"

out=$(printf '{"prompt":"p","cwd":"%s"}' "$CLONE_B" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_A" "$HOOK")
if [ -z "$out" ]; then
  pass "T17: armed marker in clone-a does not block UserPromptSubmit from clone-b"
else
  fail "T17: expected clone-b prompt unblocked by foreign clone-a marker: out='$out'"
fi

out=$(printf '{"prompt":"p","cwd":"%s"}' "$CLONE_A" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_A" "$HOOK")
case "$out" in
  *'"decision":"block"'*) pass "T17: armed marker in clone-a still blocks UserPromptSubmit from clone-a (owning clone)" ;;
  *) fail "T17: expected clone-a prompt blocked by own clone-a marker: out='$out'" ;;
esac

out=$(printf '{"prompt":"p","cwd":"%s"}' "$CLONE_A" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_B" "$HOOK")
if [ -z "$out" ]; then
  pass "T17: armed marker in clone-b does not block UserPromptSubmit from clone-a"
else
  fail "T17: expected clone-a prompt unblocked by foreign clone-b marker: out='$out'"
fi

out=$(printf '{"prompt":"p","cwd":"%s"}' "$CLONE_B" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_B" "$HOOK")
case "$out" in
  *'"decision":"block"'*) pass "T17: armed marker in clone-b still blocks UserPromptSubmit from clone-b (owning clone)" ;;
  *) fail "T17: expected clone-b prompt blocked by own clone-b marker: out='$out'" ;;
esac

# --- T20: subdirectory cwd within owning clone still blocks (#5927) ---
CLONE_A_SUB="$CLONE_A/docs"
mkdir -p "$CLONE_A_SUB"
out=$(printf '{"prompt":"p","cwd":"%s"}' "$CLONE_A_SUB" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_A" "$HOOK")
case "$out" in
  *'"decision":"block"'*) pass "T20: subdirectory cwd still blocked for owning clone" ;;
  *) fail "T20: subdirectory cwd bypassed armed breaker: out='$out'" ;;
esac

rm -f "$D_A/no-progress-turns.count" "$D_A/no-progress-circuit-breaker-armed"
printf '%s\n' "PID=$$" "CLAUDE_PID=$$" "START_EPOCH=$(( $(date +%s) - 10 ))" "STEP=design-step3-review" "TIMEOUT_S=21600" "CLONE_PATH=$CLONE_A" >"$MARKER_A"
write_keepalive "$D_A" "$CLONE_B"
out=$(printf '{"stop_hook_active":false,"cwd":"%s"}' "$CLONE_A" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_A" "$HOOK")
cnt=$(cat "$D_A/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
  pass "T17: Stop path prefers marker-local same-clone CLONE_PATH over conflicting keepalive"
else
  fail "T17: marker-local same-clone CLONE_PATH should count Stop: out='$out' cnt=$cnt"
fi
touch "$D_A/no-progress-circuit-breaker-armed"
out=$(printf '{"prompt":"p","cwd":"%s"}' "$CLONE_A" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_A" "$HOOK")
case "$out" in
  *'"decision":"block"'*) pass "T17: UserPromptSubmit prefers marker-local same-clone CLONE_PATH over conflicting keepalive" ;;
  *) fail "T17: marker-local same-clone CLONE_PATH should block prompt: out='$out'" ;;
esac

rm -f "$D_A/no-progress-turns.count" "$D_A/no-progress-circuit-breaker-armed"
printf '%s\n' "PID=$$" "CLAUDE_PID=$$" "START_EPOCH=$(( $(date +%s) - 10 ))" "STEP=design-step3-review" "TIMEOUT_S=21600" "CLONE_PATH=$CLONE_B" >"$MARKER_A"
write_keepalive "$D_A" "$CLONE_A"
out=$(printf '{"stop_hook_active":false,"cwd":"%s"}' "$CLONE_A" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_A" "$HOOK")
cnt=$(cat "$D_A/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 0 ]; then
  pass "T17: Stop path prefers marker-local foreign CLONE_PATH over conflicting keepalive"
else
  fail "T17: marker-local foreign CLONE_PATH should skip Stop count: out='$out' cnt=$cnt"
fi
touch "$D_A/no-progress-circuit-breaker-armed"
out=$(printf '{"prompt":"p","cwd":"%s"}' "$CLONE_A" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_A" "$HOOK")
if [ -z "$out" ]; then
  pass "T17: UserPromptSubmit prefers marker-local foreign CLONE_PATH over conflicting keepalive"
else
  fail "T17: marker-local foreign CLONE_PATH should not block prompt: out='$out'"
fi

rm -f "$D_A/no-progress-turns.count" "$D_A/no-progress-circuit-breaker-armed"
printf '%s\n' "PID=$$" "CLAUDE_PID=$$" "START_EPOCH=$(( $(date +%s) - 10 ))" "STEP=design-step3-review" "TIMEOUT_S=21600" >"$MARKER_A"
write_keepalive "$D_A" "$CLONE_A"
out=$(printf '{"stop_hook_active":false,"cwd":"%s"}' "$CLONE_A_SUB" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_A" "$HOOK")
cnt=$(cat "$D_A/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
  pass "T17: marker without CLONE_PATH falls back to keepalive for Stop"
else
  fail "T17: keepalive fallback should count Stop: out='$out' cnt=$cnt"
fi

rm -f "$MARKER_A" "$MARKER_B" "$D_A/.larch-keepalive" "$D_B/.larch-keepalive" \
      "$D_A/no-progress-circuit-breaker-armed" "$D_B/no-progress-circuit-breaker-armed"

# --- T18: unknown clone identity (no .larch-keepalive) still blocks regardless of cwd (fail-safe default) ---
rm -f "$D/no-progress-turns.count" "$D/no-progress-circuit-breaker-armed" "$MARKER"
write_marker $$ "$(( $(date +%s) - 10 ))" 21600 implement-step3-checks
touch "$D/no-progress-circuit-breaker-armed"
out=$(printf '{"prompt":"p","cwd":"%s"}' "$CLONE_A" | LARCH_BG_POLL_GUARD_MARKER="$MARKER" "$HOOK")
case "$out" in
  *'"decision":"block"'*) pass "T18: marker with no .larch-keepalive still blocks regardless of cwd mismatch" ;;
  *) fail "T18: expected block for unknown-clone marker (fail-safe default): out='$out'" ;;
esac
rm -f "$D/no-progress-circuit-breaker-armed" "$D/no-progress-turns.count" "$MARKER"

# --- T19: block message identifies exact marker path and recovery files (#5927) ---
write_marker $$ "$(( $(date +%s) - 10 ))" 21600 implement-step3-checks
touch "$D/no-progress-circuit-breaker-armed"
out=$(LARCH_BG_POLL_GUARD_MARKER="$MARKER" run_hook "$(prompt_event)")
D_CANON=$(cd "$D" && pwd -P)
case "$out" in
  *"$D_CANON/.bg-wait-active"*"$D_CANON/no-progress-circuit-breaker-armed"*"$D_CANON/no-progress-turns.count"*)
    pass "T19: block message includes marker path and recovery file paths" ;;
  *) fail "T19: expected marker/recovery paths in message: out='$out'" ;;
esac
rm -f "$D/no-progress-circuit-breaker-armed" "$D/no-progress-turns.count" "$MARKER"

# --- T21: Stop-path counter is clone-scoped (#5927 follow-up) ---
# A Stop fired from a FOREIGN clone must not increment an unrelated clone's
# marker counter. Previously every clone's Stop bumped every live marker, so a
# slow-but-live wait armed its own breaker from other clones' turn activity and
# the owning clone then blocked its own next prompt. A Stop from the marker's
# OWN clone must still increment (owning-session protection preserved).
D_SCOPE="$TMP/claude-design-scopeclone-marker"
mkdir -p "$D_SCOPE"
CLONE_SCOPE="$TMP/scope-owner-repo"
CLONE_FOREIGN="$TMP/scope-foreign-repo"
mkdir -p "$CLONE_SCOPE" "$CLONE_FOREIGN"
MARKER_SCOPE="$D_SCOPE/.bg-wait-active"
printf '%s\n' "PID=$$" "CLAUDE_PID=$$" "START_EPOCH=$(( $(date +%s) - 10 ))" "STEP=design-step3-review" "TIMEOUT_S=21600" >"$MARKER_SCOPE"
printf 'CLONE_PATH=%s\nSESSION_ID=test-scope-owner\n' "$CLONE_SCOPE" >"$D_SCOPE/.larch-keepalive"

out=$(printf '{"stop_hook_active":false,"cwd":"%s"}' "$CLONE_FOREIGN" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_SCOPE" "$HOOK")
cnt=$(cat "$D_SCOPE/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 0 ]; then
  pass "T21: Stop from foreign clone does not increment unrelated marker counter"
else
  fail "T21: foreign-clone Stop must not count: out='$out' cnt=$cnt"
fi

out=$(printf '{"stop_hook_active":false,"cwd":"%s"}' "$CLONE_SCOPE" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_SCOPE" "$HOOK")
cnt=$(cat "$D_SCOPE/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
  pass "T21: Stop from owning clone still increments marker counter"
else
  fail "T21: owning-clone Stop must count: out='$out' cnt=$cnt"
fi

# Repeated foreign-clone Stops must never arm an unrelated marker's breaker,
# even at a low threshold — this is the core cross-session-arming regression.
rm -f "$D_SCOPE/no-progress-turns.count" "$D_SCOPE/no-progress-circuit-breaker-armed"
for _ in 1 2 3; do
  printf '{"stop_hook_active":false,"cwd":"%s"}' "$CLONE_FOREIGN" | \
    LARCH_BG_POLL_GUARD_MARKER="$MARKER_SCOPE" LARCH_NO_PROGRESS_GUARD_THRESHOLD=2 "$HOOK" >/dev/null
done
if [ ! -f "$D_SCOPE/no-progress-circuit-breaker-armed" ]; then
  pass "T21: repeated foreign-clone Stops never arm an unrelated marker's breaker"
else
  fail "T21: foreign-clone Stops armed an unrelated marker's breaker"
fi

# Fail-safe default: a marker with no .larch-keepalive (unknown clone identity)
# must still count from any cwd, so the owning session's breaker is never lost.
rm -f "$D_SCOPE/.larch-keepalive" "$D_SCOPE/no-progress-turns.count" "$D_SCOPE/no-progress-circuit-breaker-armed"
out=$(printf '{"stop_hook_active":false,"cwd":"%s"}' "$CLONE_FOREIGN" | LARCH_BG_POLL_GUARD_MARKER="$MARKER_SCOPE" "$HOOK")
cnt=$(cat "$D_SCOPE/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 1 ]; then
  pass "T21: marker without .larch-keepalive still counts from any cwd (fail-safe default)"
else
  fail "T21: unknown-identity marker must still count: out='$out' cnt=$cnt"
fi
rm -f "$MARKER_SCOPE"

# --- T22: many TMPDIR larch-*/claude-*-prefixed dirs stay well under the hook's 10s
# budget and correct discovery still finds/counts the live marker (#5943 regression
# guard: marker_candidates() used to spawn one find subprocess per matched dir).
mkdir -p "$TMP"/larch-perf-{1..3000}
D_PERF="$TMP/claude-implement-perf-xyz"
mkdir -p "$D_PERF"
MARKER_PERF="$D_PERF/.bg-wait-active"
printf '%s\n' "PID=$$" "CLAUDE_PID=$$" "START_EPOCH=$(( $(date +%s) - 10 ))" "STEP=implement-step3-checks" "TIMEOUT_S=21600" >"$MARKER_PERF"
rm -f "$D_PERF/no-progress-turns.count"
start_ts=$(date +%s)
out=$(printf '{"stop_hook_active":false,"cwd":"%s"}' "$D_PERF" | "$HOOK")
elapsed=$(( $(date +%s) - start_ts ))
cnt=$(cat "$D_PERF/no-progress-turns.count" 2>/dev/null || echo 0)
if [ -z "$out" ] && [ "$cnt" -eq 1 ] && [ "$elapsed" -le 5 ]; then
  pass "T22: discovery over 3000 TMPDIR session dirs stays bounded (elapsed=${elapsed}s) and finds the live marker"
else
  fail "T22: expected count=1 and elapsed<=5s over 3000 dirs: out='$out' cnt=$cnt elapsed=${elapsed}s"
fi
rm -f "$MARKER_PERF"
rm -rf "$TMP"/larch-perf-*

# --- Summary ---
printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
