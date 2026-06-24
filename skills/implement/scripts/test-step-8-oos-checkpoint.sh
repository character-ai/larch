#!/usr/bin/env bash
# test-step-8-oos-checkpoint.sh — offline harness for the Step 8 OOS checkpoint wrapper.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/step-8-oos-checkpoint.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
PASS=0
FAIL=0
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-step-8-oos-checkpoint.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains() { local n=$1 h=$2 l=$3; if printf '%s' "$h" | grep -Fq -- "$n"; then pass "$l"; else fail "$l (missing: $n)"; fi; }
assert_not_contains() { local n=$1 h=$2 l=$3; if printf '%s' "$h" | grep -Fq -- "$n"; then fail "$l (unexpected: $n)"; else pass "$l"; fi; }
assert_rc() { local a=$1 e=$2 l=$3; if [ "$a" -eq "$e" ]; then pass "$l"; else fail "$l (expected rc=$e got rc=$a)"; fi; }

helper_text=$(cat "$HELPER")
assert_contains 'implement step-8-oos-checkpoint' "$helper_text" 'static: delegates to Python checkpoint router'
assert_not_contains 'oos disposition-checkpoint' "$helper_text" 'static: no direct disposition-checkpoint call'

IMPL_TMP="$TMP_ROOT/implement"
mkdir -p "$IMPL_TMP"
printf 'export CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT" >"$IMPL_TMP/plugin-root.env"
REAL_PYTHON=$(command -v python3)
STUB_BIN="$TMP_ROOT/bin"
mkdir -p "$STUB_BIN"
cat >"$STUB_BIN/python3" <<EOF_STUB
#!/usr/bin/env bash
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "implement" ] && [ "\$3" = "step-8-oos-checkpoint" ]; then
  printf '%s\n' 'OOS_CHECKPOINT_RC=1'
  printf '%s\n' 'NEXT_ACTION=stall'
  exit 0
fi
exec "$REAL_PYTHON" "\$@"
EOF_STUB
chmod +x "$STUB_BIN/python3"

set +e
OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" 2>"$TMP_ROOT/stderr.txt")
RC=$?
set -e
assert_rc "$RC" 0 'dynamic: wrapper exit equals Python rc, not disposition diagnostic rc'
assert_contains 'OOS_CHECKPOINT_RC=1' "$OUT" 'dynamic: relays checkpoint rc kv'
assert_contains 'NEXT_ACTION=stall' "$OUT" 'dynamic: relays NEXT_ACTION kv'

cat >"$STUB_BIN/python3" <<EOF_STUB2
#!/usr/bin/env bash
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "implement" ] && [ "\$3" = "step-8-oos-checkpoint" ]; then
  printf '%s\n' 'OOS_CHECKPOINT_RC=2'
  printf '%s\n' 'NEXT_ACTION=stall'
  exit 0
fi
exec "$REAL_PYTHON" "\$@"
EOF_STUB2
chmod +x "$STUB_BIN/python3"
printf 'child validation detail\n' >"$IMPL_TMP/oos-disposition-checkpoint.stderr.log"
PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" >/dev/null
assert_contains 'child validation detail' "$(cat "$IMPL_TMP/oos-disposition-checkpoint.stderr.log")" 'dynamic: wrapper does not truncate child-written stderr log'

if [ "$FAIL" -eq 0 ]; then
  printf 'PASS: test-step-8-oos-checkpoint.sh (%d assertions)\n' "$PASS"
  exit 0
fi
printf 'FAIL: test-step-8-oos-checkpoint.sh (%d passed, %d failed)\n' "$PASS" "$FAIL" >&2
exit 1
