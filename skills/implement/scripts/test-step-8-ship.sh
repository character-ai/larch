#!/usr/bin/env bash
# test-step-8-ship.sh — offline harness for step-8-ship.sh contracts.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/step-8-ship.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
PASS=0
FAIL=0
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-step-8-ship.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains() { local n=$1 h=$2 l=$3; if printf '%s' "$h" | grep -Fq -- "$n"; then pass "$l"; else fail "$l (missing: $n)"; fi; }
assert_rc() { local a=$1 e=$2 l=$3; if [ "$a" -eq "$e" ]; then pass "$l"; else fail "$l (expected rc=$e got rc=$a)"; fi; }

helper_text=$(cat "$HELPER")
assert_contains 'sys.version_info >= (3, 11)' "$helper_text" 'static: python 3.11 guard present'
# shellcheck disable=SC2016
assert_contains 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr' "$helper_text" 'static: python ship CLI invoked'
# shellcheck disable=SC2016
assert_contains '--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"' "$helper_text" 'static: state file forwarded'
# shellcheck disable=SC2016
assert_contains '--no-logs-commit "$NO_LOGS_COMMIT_RESOLVED"' "$helper_text" 'static: no-logs-commit forwarded'
if printf '%s' "$helper_text" | grep -Fq 'retired_ship_driver_selector'; then
  fail 'static: retired selector absent'
else
  pass 'static: retired selector absent'
fi

IMPL_TMP="$TMP_ROOT/implement"
mkdir -p "$IMPL_TMP"
printf 'BRANCH_NAME=test-branch\nISSUE_NUMBER=42\nRUN_ID=run-ship-guard\nREPO=owner/repo\nMANIFEST_PATH=/tmp/manifest.json\n' >"$IMPL_TMP/ship-pr-state.sh"
printf 'export CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT" >"$IMPL_TMP/plugin-root.env"
printf 'session-id\n' >"$IMPL_TMP/session-id"

REAL_PYTHON=$(command -v python3)
STUB_BIN="$TMP_ROOT/bin"
mkdir -p "$STUB_BIN"
cat >"$STUB_BIN/python3" <<EOF_STUB
#!/usr/bin/env bash
if [ "\$1" = "-c" ] && printf '%s\n' "\$2" | grep -Fq 'sys.version_info >= (3, 11)'; then
  exit 0
fi
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "ship" ] && [ "\$3" = "pr" ]; then
  printf '%s\n' "\$@" > "$TMP_ROOT/ship-argv.txt"
  printf '%s\n' '{"outcome":"OK","detail":"stub"}'
  exit 0
fi
exec "$REAL_PYTHON" "\$@"
EOF_STUB
chmod +x "$STUB_BIN/python3"

set +e
OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" 2>"$TMP_ROOT/stderr.txt")
RC=$?
set -e
assert_rc "$RC" 0 'dynamic: wrapper exits with python driver rc'
assert_contains 'ship' "$(cat "$TMP_ROOT/ship-argv.txt")" 'dynamic: invokes cli ship pr domain'
assert_contains 'pr' "$(cat "$TMP_ROOT/ship-argv.txt")" 'dynamic: invokes cli ship pr verb'
assert_contains '--branch' "$(cat "$TMP_ROOT/ship-argv.txt")" 'dynamic: forwards branch flag'
assert_contains 'test-branch' "$(cat "$TMP_ROOT/ship-argv.txt")" 'dynamic: forwards branch value'
assert_contains '"outcome":"OK"' "$OUT" 'dynamic: forwards stdout JSON'

cat >"$STUB_BIN/python3" <<EOF_STALE
#!/usr/bin/env bash
if [ "\$1" = "-c" ] && printf '%s\n' "\$2" | grep -Fq 'sys.version_info >= (3, 11)'; then
  exit 1
fi
exec "$REAL_PYTHON" "\$@"
EOF_STALE
chmod +x "$STUB_BIN/python3"
set +e
OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" 2>"$TMP_ROOT/stderr.txt")
RC=$?
set -e
assert_rc "$RC" 4 'dynamic: stale python exits 4'
assert_contains '"outcome":"STALLED"' "$OUT" 'dynamic: stale python emits STALLED JSON'

if [ "$FAIL" -eq 0 ]; then
  printf 'PASS: test-step-8-ship.sh (%d assertions)\n' "$PASS"
  exit 0
fi
printf 'FAIL: test-step-8-ship.sh (%d passed, %d failed)\n' "$PASS" "$FAIL" >&2
exit 1
