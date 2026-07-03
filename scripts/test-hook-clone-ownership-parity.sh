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
    in_fn { print }
    in_fn && $0 == "}" { exit }
  ' "$file"
}

compare_function() {
  local name="$1" tmp_bg tmp_np
  tmp_bg=$(mktemp "${TMPDIR:-/tmp}/hook-clone-bg.XXXXXX") || exit 1
  tmp_np=$(mktemp "${TMPDIR:-/tmp}/hook-clone-np.XXXXXX") || { rm -f "$tmp_bg"; exit 1; }
  trap 'rm -f "$tmp_bg" "$tmp_np"' RETURN
  extract_function "$BG_HOOK" "$name" >"$tmp_bg"
  extract_function "$NO_PROGRESS_HOOK" "$name" >"$tmp_np"
  if [ ! -s "$tmp_bg" ] || [ ! -s "$tmp_np" ]; then
    fail "$name exists in both hooks"
    diff -u "$tmp_bg" "$tmp_np" || true
    return
  fi
  if diff -u "$tmp_bg" "$tmp_np" >/dev/null; then
    pass "$name stays byte-identical across hook copies"
  else
    fail "$name drifted between hook-bg-poll-guard.sh and hook-no-progress-guard.sh"
    diff -u "$tmp_bg" "$tmp_np" || true
  fi
}

compare_function clone_paths_same
compare_function marker_foreign_clone

printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
