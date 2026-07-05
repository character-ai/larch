#!/usr/bin/env bash
# test-hook-clone-ownership-parity.sh — ensure duplicated hook clone-ownership helpers do not drift.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
BG_HOOK="$SCRIPT_DIR/hook-bg-poll-guard.sh"
NO_PROGRESS_HOOK="$SCRIPT_DIR/hook-no-progress-guard.sh"

PASS=0
FAIL=0
pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }

extract_function() {
  local file="$1" name="$2"
  awk -v name="$name" '
    $0 == name "() {" { in_fn=1 }
    in_fn {
      print
      line=$0
      opens=gsub(/\{/, "", line)
      line=$0
      closes=gsub(/\}/, "", line)
      depth += opens - closes
      if (depth == 0) { exit }
    }
  ' "$file"
}

strip_renamed_function_noise() {
  sed '1d' | awk '
    /^[[:space:]]*#/ { next }
    { print }
  '
}

compare_function() {
  local name="$1" tmp_bg tmp_np
  tmp_bg=$(mktemp "${TMPDIR:-/tmp}/hook-clone-bg.XXXXXX") || exit 1
  tmp_np=$(mktemp "${TMPDIR:-/tmp}/hook-clone-np.XXXXXX") || { rm -f "$tmp_bg"; exit 1; }
  extract_function "$BG_HOOK" "$name" >"$tmp_bg"
  extract_function "$NO_PROGRESS_HOOK" "$name" >"$tmp_np"
  if [ ! -s "$tmp_bg" ] || [ ! -s "$tmp_np" ]; then
    fail "$name exists in both hooks"
    diff -u "$tmp_bg" "$tmp_np" || true
    rm -f "$tmp_bg" "$tmp_np"
    return
  fi
  if diff -u "$tmp_bg" "$tmp_np" >/dev/null; then
    pass "$name stays byte-identical across hook copies"
  else
    fail "$name drifted between hook-bg-poll-guard.sh and hook-no-progress-guard.sh"
    diff -u "$tmp_bg" "$tmp_np" || true
  fi
  rm -f "$tmp_bg" "$tmp_np"
}

compare_renamed_pair() {
  local left_file="$1" left_name="$2" right_file="$3" right_name="$4" tmp_left tmp_right
  tmp_left=$(mktemp "${TMPDIR:-/tmp}/hook-clone-left.XXXXXX") || exit 1
  tmp_right=$(mktemp "${TMPDIR:-/tmp}/hook-clone-right.XXXXXX") || { rm -f "$tmp_left"; exit 1; }
  extract_function "$left_file" "$left_name" | strip_renamed_function_noise >"$tmp_left"
  extract_function "$right_file" "$right_name" | strip_renamed_function_noise >"$tmp_right"
  if [ ! -s "$tmp_left" ] || [ ! -s "$tmp_right" ]; then
    fail "$left_name/$right_name exists in both hooks"
    diff -u "$tmp_left" "$tmp_right" || true
    rm -f "$tmp_left" "$tmp_right"
    return
  fi
  if diff -u "$tmp_left" "$tmp_right" >/dev/null; then
    pass "$left_name/$right_name stays comment-stripped identical across hook copies"
  else
    fail "$left_name drifted from $right_name beyond comments or the renamed header"
    diff -u "$tmp_left" "$tmp_right" || true
  fi
  rm -f "$tmp_left" "$tmp_right"
}


test_extract_function_nested_body_fixture() {
  if (
    PASS=0
    FAIL=0
    tmp_hook=$(mktemp "${TMPDIR:-/tmp}/hook-clone-nested.XXXXXX") || exit 1
    tmp_body=$(mktemp "${TMPDIR:-/tmp}/hook-clone-body.XXXXXX") || { rm -f "$tmp_hook"; exit 1; }
    trap 'rm -f "$tmp_hook" "$tmp_body"' EXIT
    cat >"$tmp_hook" <<'EOF'
nested_fn() {
  if true; then
    {
      printf '%s\n' nested
    }
  fi
  printf '%s\n' post-nested-drift-line
}
EOF
    extract_function "$tmp_hook" nested_fn >"$tmp_body"
    grep -Fq 'post-nested-drift-line' "$tmp_body"
  ); then
    pass "extract_function keeps body lines after nested brace groups"
  else
    fail "extract_function truncated a nested-brace fixture"
  fi
}

test_compare_renamed_pair_drift_fixture() {
  if (
    PASS=0
    FAIL=0
    tmp_left=$(mktemp "${TMPDIR:-/tmp}/hook-clone-left-fixture.XXXXXX") || exit 1
    tmp_right=$(mktemp "${TMPDIR:-/tmp}/hook-clone-right-fixture.XXXXXX") || { rm -f "$tmp_left"; exit 1; }
    trap 'rm -f "$tmp_left" "$tmp_right"' EXIT
    cat >"$tmp_left" <<'EOF'
left_fn() {
  printf '%s\n' shared
  printf '%s\n' left-only
}
EOF
    cat >"$tmp_right" <<'EOF'
right_fn() {
  printf '%s\n' shared
  printf '%s\n' right-only
}
EOF
    compare_rc=0
    if compare_renamed_pair "$tmp_left" left_fn "$tmp_right" right_fn >/dev/null 2>&1; then
      compare_rc=0
    else
      compare_rc=$?
    fi
    [ "$compare_rc" -ne 0 ] || [ "$FAIL" -gt 0 ]
  ); then
    pass "compare_renamed_pair reports deliberate fixture drift"
  else
    fail "compare_renamed_pair missed deliberate fixture drift"
  fi
}

test_extract_function_nested_body_fixture
test_compare_renamed_pair_drift_fixture

compare_function canonical_dir
compare_function marker_value
compare_function marker_candidates
compare_function clone_paths_same
compare_function marker_foreign_clone
compare_renamed_pair "$BG_HOOK" marker_step_completed "$NO_PROGRESS_HOOK" is_step_completed
# marker_is_live (hook-bg-poll-guard.sh) and is_marker_live
# (hook-no-progress-guard.sh) share a semantic role but intentionally differ in
# parent-guard return codes, reset_no_progress_state missing-marker behavior,
# and the LIVE_MARKER_DIR side effect owned by no-progress-guard.
# Byte-identical comparison is not applicable; each hook's own tests cover its
# liveness logic.

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
