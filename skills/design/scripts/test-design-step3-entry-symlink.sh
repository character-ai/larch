#!/usr/bin/env bash
# test-design-step3-entry-symlink.sh — swapped session-env symlink must be refused
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
STATE="$ROOT/skills/design/scripts/design-step3-entry-state.sh"
PREVIEW="$ROOT/skills/design/scripts/design-step3-entry-preview.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

HOME_DIR="$(mktemp -d "${TMPDIR:-/tmp}/test-step3-symlink-home.XXXXXX")"
SESSIONS="$HOME_DIR/.cache/larch/sessions"
mkdir -p "$SESSIONS"
printf 'export DESIGN_TMPDIR=/tmp\n' >"$SESSIONS/real-env.sh"
# Swapped symlink: wrong PID key (99999) for the supplied PID (12345), so the
# trusted resolver must refuse and the wrapper must fail closed at source time.
SWAPPED="$SESSIONS/current-design-env-99999.sh"
ln -s "$SESSIONS/real-env.sh" "$SWAPPED"

set +e
env HOME="$HOME_DIR" CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$STATE" --session-env-path "$SWAPPED" --claude-pid 12345 2>"$HOME_DIR/state.err"
state_rc=$?
env HOME="$HOME_DIR" CLAUDE_PLUGIN_ROOT="$ROOT" \
  "$PREVIEW" --session-env-path "$SWAPPED" --claude-pid 12345 2>"$HOME_DIR/preview.err"
preview_rc=$?
set -e

[[ "$state_rc" -ne 0 ]] || fail "entry-state accepted swapped session-env symlink (rc=$state_rc)"
grep -Fq 'refusing untrusted session-env symlink' "$HOME_DIR/state.err" \
  || fail "entry-state did not log refusal: $(cat "$HOME_DIR/state.err")"
[[ "$preview_rc" -ne 0 ]] || fail "entry-preview accepted swapped session-env symlink (rc=$preview_rc)"
grep -Fq 'refusing untrusted session-env symlink' "$HOME_DIR/preview.err" \
  || fail "entry-preview did not log refusal: $(cat "$HOME_DIR/preview.err")"

rm -rf "$HOME_DIR"
pass 'Step 3 entry wrappers refuse a swapped session-env symlink'
pass 'design-step3-entry-symlink checks passed'
