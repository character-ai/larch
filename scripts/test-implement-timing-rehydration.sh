#!/usr/bin/env bash
# Regression test for /implement timing-ledger rehydration.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

count_fixed() {
  local needle="$1"
  grep -Fxc "$needle" "$SKILL_MD" || true
}

[[ -f "$SKILL_MD" ]] || fail "skills/implement/SKILL.md missing"

old_export_count="$(count_fixed 'export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE')"
[[ "$old_export_count" == "0" ]] \
  || fail "stale two-key rehydration export remains ($old_export_count matches)"

new_export_count="$(count_fixed 'export LARCH_TOKEN_SESSION_ID LARCH_CLAUDE_SOURCE_FILE LARCH_TIMING_LEDGER')"
(( new_export_count >= 17 )) \
  || fail "expected at least 17 timing-aware rehydration exports, found $new_export_count"

# shellcheck disable=SC2016 # literal SKILL.md shell template, not this script's env
token_read_count="$(count_fixed 'LARCH_TOKEN_SESSION_ID=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TOKEN_SESSION_ID --default "")')"
# shellcheck disable=SC2016 # literal SKILL.md shell template, not this script's env
timing_read_count="$(count_fixed 'LARCH_TIMING_LEDGER=$("${CLAUDE_PLUGIN_ROOT}/scripts/read-session-env-key.sh" --file "$IMPLEMENT_TMPDIR/session-env.sh" --key LARCH_TIMING_LEDGER --default "")')"
[[ "$timing_read_count" == "$token_read_count" ]] \
  || fail "LARCH_TIMING_LEDGER read count ($timing_read_count) does not match LARCH_TOKEN_SESSION_ID read count ($token_read_count)"

# shellcheck disable=SC2016 # literal SKILL.md shell template, not this script's env
tmpdir_assign_count="$(count_fixed 'IMPLEMENT_TMPDIR="$IMPLEMENT_TMPDIR"')"
tmpdir_export_count="$(count_fixed 'export IMPLEMENT_TMPDIR')"
[[ "$tmpdir_assign_count" == "$token_read_count" ]] \
  || fail "IMPLEMENT_TMPDIR assignment count ($tmpdir_assign_count) does not match token rehydration count ($token_read_count)"
[[ "$tmpdir_export_count" == "$token_read_count" ]] \
  || fail "IMPLEMENT_TMPDIR export count ($tmpdir_export_count) does not match token rehydration count ($token_read_count)"

echo "PASS: test-implement-timing-rehydration.sh"
