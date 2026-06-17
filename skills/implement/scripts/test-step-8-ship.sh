#!/usr/bin/env bash
# test-step-8-ship.sh — offline harness for Step 8 ship wrappers.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/step-8-ship.sh"
GUARD="$SCRIPT_DIR/step-8-python-guard.sh"
SEEDER="$SCRIPT_DIR/step-8-seed-initial.sh"
CLONE_LIB="$SCRIPT_DIR/lib-implement-clone-tag.sh"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
PASS=0
FAIL=0
TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/test-step-8-ship.XXXXXX")"
trap 'rm -rf "$TMP_ROOT"' EXIT

pass() { PASS=$((PASS + 1)); printf 'PASS: %s\n' "$1"; }
fail() { FAIL=$((FAIL + 1)); printf 'FAIL: %s\n' "$1" >&2; }
assert_contains() { local n=$1 h=$2 l=$3; if printf '%s' "$h" | grep -Fq -- "$n"; then pass "$l"; else fail "$l (missing: $n)"; fi; }
assert_not_contains() { local n=$1 h=$2 l=$3; if printf '%s' "$h" | grep -Fq -- "$n"; then fail "$l (unexpected: $n)"; else pass "$l"; fi; }
assert_rc() { local a=$1 e=$2 l=$3; if [ "$a" -eq "$e" ]; then pass "$l"; else fail "$l (expected rc=$e got rc=$a)"; fi; }

helper_text=$(cat "$HELPER")
assert_contains 'lib-implement-clone-tag.sh' "$helper_text" 'static: clone-tag helper sourced'
assert_contains 'step-8-python-guard.sh' "$helper_text" 'static: shared python guard invoked'
assert_contains 'phantom-probe-with-warn.sh --step 8-pre-ship >&2' "$helper_text" 'static: bundled phantom probe redirects stdout'
assert_not_contains 'sys.version_info >= (3, 11)' "$helper_text" 'static: inline python version guard absent from ship wrapper'
# shellcheck disable=SC2016
assert_not_contains 'claude-implement-${CLONE_TAG_FULL}-' "$helper_text" 'static: inline tmpdir prefix absent from ship wrapper'
# shellcheck disable=SC2016
assert_contains 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr' "$helper_text" 'static: python ship CLI invoked'
# shellcheck disable=SC2016
assert_contains '--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"' "$helper_text" 'static: state file forwarded'
# shellcheck disable=SC2016
assert_contains '--expected-tmpdir-basename-prefix "$EXPECTED_TMPDIR_BASENAME_PREFIX"' "$helper_text" 'static: shared prefix forwarded'

seeder_text=$(cat "$SEEDER")
assert_contains 'ship seed-initial-state' "$seeder_text" 'static: seeder wrapper delegates to Python seeder'
# shellcheck disable=SC2016
assert_contains 'session read-key --file "$file"' "$seeder_text" 'static: seeder reads session keys through python cli'
assert_not_contains 'read-session-env-key.sh' "$seeder_text" 'static: retired session reader absent'
assert_contains 'lib-implement-clone-tag.sh' "$seeder_text" 'static: seeder sources clone helper'

IMPL_TMP="$TMP_ROOT/implement"
mkdir -p "$IMPL_TMP"
printf 'BRANCH_NAME=test-branch\nISSUE_NUMBER=42\nRUN_ID=run-ship-guard\nREPO=owner/repo\nMANIFEST_PATH=/tmp/manifest.json\nNO_ADMIN_FALLBACK=true\nNO_LOGS_COMMIT=true\n' >"$IMPL_TMP/ship-pr-state.sh"
printf 'export CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT" >"$IMPL_TMP/plugin-root.env"
printf 'session-id\n' >"$IMPL_TMP/session-id"
cat >"$IMPL_TMP/larch-run.sh" <<EOF_RUN
#!/usr/bin/env bash
set -euo pipefail
case "\$1" in
  skills/implement/scripts/step-8-python-guard.sh) printf '%s\n' guard >> "$TMP_ROOT/order.txt"; exit 0 ;;
  scripts/phantom-probe-with-warn.sh) printf '%s\n' phantom >> "$TMP_ROOT/order.txt"; printf '%s\n' 'PHANTOM_STATUS=clean'; exit 0 ;;
  *) exec bash "$REPO_ROOT/\$1" "\${@:2}" ;;
esac
EOF_RUN
chmod +x "$IMPL_TMP/larch-run.sh"

REAL_PYTHON=$(command -v python3)
STUB_BIN="$TMP_ROOT/bin"
mkdir -p "$STUB_BIN"
cat >"$STUB_BIN/python3" <<EOF_STUB
#!/usr/bin/env bash
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "ship" ] && [ "\$3" = "pr" ]; then
  printf '%s\n' driver >> "$TMP_ROOT/order.txt"
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
assert_contains $'guard\nphantom\ndriver' "$(cat "$TMP_ROOT/order.txt")" 'dynamic: guard then phantom then driver order'
assert_contains 'PHANTOM_STATUS=clean' "$(cat "$TMP_ROOT/stderr.txt")" 'dynamic: phantom stdout redirected to stderr'
assert_not_contains 'PHANTOM_STATUS=clean' "$OUT" 'dynamic: phantom output absent from wrapper stdout'
assert_contains '"outcome":"OK"' "$OUT" 'dynamic: forwards stdout JSON only'
assert_contains '--branch' "$(cat "$TMP_ROOT/ship-argv.txt")" 'dynamic: forwards branch flag'
assert_contains 'test-branch' "$(cat "$TMP_ROOT/ship-argv.txt")" 'dynamic: forwards branch value'
assert_contains '--expected-tmpdir-basename-prefix' "$(cat "$TMP_ROOT/ship-argv.txt")" 'dynamic: forwards shared prefix flag'

cat >"$STUB_BIN/python3" <<EOF_OLD
#!/usr/bin/env bash
if [ "\$1" = "-c" ]; then exit 1; fi
exec "$REAL_PYTHON" "\$@"
EOF_OLD
chmod +x "$STUB_BIN/python3"
set +e
GUARD_OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$GUARD" 2>"$TMP_ROOT/guard-stderr.txt")
GUARD_RC=$?
set -e
assert_rc "$GUARD_RC" 4 'guard: stale python exits 4'
assert_contains 'ERROR: Python ship driver requires Python 3.11 or newer' "$(cat "$TMP_ROOT/guard-stderr.txt")" 'guard: stale python emits stderr'
assert_contains '"outcome":"STALLED"' "$GUARD_OUT" 'guard: stale python emits STALLED JSON'

cat >"$STUB_BIN/python3" <<EOF_NEW
#!/usr/bin/env bash
if [ "\$1" = "-c" ]; then exit 0; fi
exec "$REAL_PYTHON" "\$@"
EOF_NEW
chmod +x "$STUB_BIN/python3"
set +e
GUARD_OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$GUARD" 2>"$TMP_ROOT/guard-ok-stderr.txt")
GUARD_RC=$?
set -e
assert_rc "$GUARD_RC" 0 'guard: new python exits 0'
if [ -z "$GUARD_OUT" ]; then
  pass 'guard: new python stdout empty'
else
  fail 'guard: new python stdout empty'
fi

CLONE_OUT=$(mkdir -p "$TMP_ROOT/repo with spaces" && cd "$TMP_ROOT/repo with spaces" && CLONE_TAG='' bash -c '. "'"$CLONE_LIB"'"; printf "%s\n" "$EXPECTED_TMPDIR_BASENAME_PREFIX"')
assert_contains 'claude-implement-repo_with_spaces-' "$CLONE_OUT" 'clone helper: derives sanitized prefix from PWD'

SEED_TMP="$TMP_ROOT/seed"
mkdir -p "$SEED_TMP/codex-step2-out"
printf 'export CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT" >"$SEED_TMP/plugin-root.env"
printf 'coder=codex\nBRANCH_NAME=seed-branch\nISSUE_NUMBER=77\nRUN_ID=run-seed\nREPO=owner/repo\nDEFERRED=true\n' >"$SEED_TMP/bootstrap-routing.env"
printf 'LARCH_RUN_ID=run-session\nREPO=owner/session\nFORKED_TARGET=false\n' >"$SEED_TMP/session-env.sh"
printf 'MERGE=true\nDRAFT=true\nNO_ADMIN_FALLBACK=true\nNO_LOGS_COMMIT=true\nMANIFEST_PATH=%s/codex-step2-out/manifest.json\n' "$SEED_TMP" >"$SEED_TMP/ship-seed-input.env"
printf '{"summary_bullets":["x"]}\n' >"$SEED_TMP/codex-step2-out/manifest.json"
printf 'seed-session\n' >"$SEED_TMP/session-id"
cat >"$STUB_BIN/python3" <<EOF_SEED
#!/usr/bin/env bash
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "session" ] && [ "\$3" = "read-key" ]; then
  file=""; key=""; default=""
  while [ "\$#" -gt 0 ]; do
    case "\$1" in --file) file=\$2; shift 2 ;; --key) key=\$2; shift 2 ;; --default) default=\$2; shift 2 ;; *) shift ;; esac
  done
  value=\$(grep "^\${key}=" "\$file" 2>/dev/null | head -n 1 | cut -d= -f2- || true)
  printf '%s\n' "\${value:-\$default}"
  exit 0
fi
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "ship" ] && [ "\$3" = "seed-initial-state" ]; then
  printf '%s\n' "\$@" > "$TMP_ROOT/seed-argv.txt"
  exit 0
fi
exec "$REAL_PYTHON" "\$@"
EOF_SEED
chmod +x "$STUB_BIN/python3"
PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$SEED_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$SEEDER" --merge false --draft false
seed_argv=$(cat "$TMP_ROOT/seed-argv.txt")
assert_contains $'--branch\nseed-branch' "$seed_argv" 'seeder: branch from bootstrap routing'
assert_contains $'--issue\n77' "$seed_argv" 'seeder: issue from bootstrap routing'
assert_contains $'--run-id\nrun-seed' "$seed_argv" 'seeder: run id from bootstrap routing'
assert_contains '--manifest-path' "$seed_argv" 'seeder: manifest path forwarded'
assert_contains $'--no-admin-fallback\ntrue' "$seed_argv" 'seeder: no-admin from ship-seed-input'
assert_contains $'--no-logs-commit\ntrue' "$seed_argv" 'seeder: no-logs from ship-seed-input'
assert_contains $'--merge\nfalse' "$seed_argv" 'seeder: stall/argv merge override precedence'
assert_contains $'--draft\nfalse' "$seed_argv" 'seeder: stall/argv draft override precedence'
assert_contains '--expected-tmpdir-basename-prefix' "$seed_argv" 'seeder: shared prefix forwarded'

if [ "$FAIL" -eq 0 ]; then
  printf 'PASS: test-step-8-ship.sh (%d assertions)\n' "$PASS"
  exit 0
fi
printf 'FAIL: test-step-8-ship.sh (%d passed, %d failed)\n' "$PASS" "$FAIL" >&2
exit 1
