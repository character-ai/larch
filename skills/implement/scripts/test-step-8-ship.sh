#!/usr/bin/env bash
# test-step-8-ship.sh — offline harness for Step 8 ship bgjob wrapper.
# shellcheck disable=SC2016 # single-quoted strings are intentional source literals.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
HELPER="$SCRIPT_DIR/step-8-ship.sh"
GUARD="$SCRIPT_DIR/step-8-python-guard.sh"
SEEDER="$SCRIPT_DIR/step-8-seed-initial.sh"
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
assert_contains 'bgjob start' "$helper_text" 'static: foreground wrapper starts bgjob'
assert_contains 'STEP="implement-step8-ship"' "$helper_text" 'static: bgjob step slug pinned'
assert_contains '--budget-s 21600' "$helper_text" 'static: bgjob budget pins Step 8 timeout'
assert_contains '--merge-result-env "$MERGE_RESULT_ENV"' "$helper_text" 'static: bgjob merge-result env passed'
assert_contains '--bgjob-child --merge-result-env "$MERGE_RESULT_ENV"' "$helper_text" 'static: bgjob child argv passed'
assert_contains 'step8_live_registry_exists' "$helper_text" 'static: live registry rejoin helper present'
assert_contains 'bgjob wait --step "$STEP" --tmpdir "$IMPLEMENT_TMPDIR" --max-wait-s 0' "$helper_text" 'static: live/completed rejoin uses bgjob wait'
assert_contains 'safe_truncate "$MERGE_RESULT_ENV"' "$helper_text" 'static: merge-result env recreated before fresh start'
assert_contains 'rm -f "$RESULT_ENV"' "$helper_text" 'static: stale canonical result env removed before fresh start'
assert_contains 'rm -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc" "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.json"' "$helper_text" 'static: stale handoff sidecars cleared before fresh start'
assert_contains 'write_merge_result_env' "$helper_text" 'static: child writes merge-result env'
assert_contains 'STEP8_HANDOFF_RC=%s' "$helper_text" 'static: merge-result env records driver rc sidecar value'
assert_contains 'STEP8_HANDOFF_JSON_PRESENT=%s' "$helper_text" 'static: merge-result env records json presence'
assert_contains 'persist_handoff "$rc"' "$helper_text" 'static: child persists real driver rc before zero exit'
assert_contains 'trap '\''persist_handoff "$?"'\'' EXIT' "$helper_text" 'static: setup failures still persist handoff through EXIT trap'
assert_contains 'python/cli.py" implement clone-tag' "$helper_text" 'static: clone-tag CLI invoked'
assert_contains 'step-8-python-guard.sh' "$helper_text" 'static: shared python guard invoked'
assert_contains 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git phantom-probe --step 8-pre-ship >&2' "$helper_text" 'static: bundled phantom probe redirects stdout'
assert_contains 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr' "$helper_text" 'static: python ship CLI invoked'
assert_contains '--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"' "$helper_text" 'static: state file forwarded'
legacy_bg='run_in'
legacy_bg="${legacy_bg}_background"
assert_not_contains "$legacy_bg" "$helper_text" 'static: helper prose/code no legacy background literal'
assert_not_contains 'printf '\''PID=%s' "$helper_text" 'static: legacy bg-wait marker writer removed'

seeder_text=$(cat "$SEEDER")
assert_contains 'ship seed-initial-state' "$seeder_text" 'static: seeder wrapper delegates to Python seeder'
assert_contains 'session read-key --file "$file"' "$seeder_text" 'static: seeder reads session keys through python cli'
assert_not_contains 'read-session-env-key.sh' "$seeder_text" 'static: retired session reader absent'
assert_contains 'python/cli.py" implement clone-tag' "$seeder_text" 'static: seeder invokes clone-tag CLI'

IMPL_TMP="$TMP_ROOT/implement"
mkdir -p "$IMPL_TMP/bgjob"
printf 'BRANCH_NAME=test-branch\nISSUE_NUMBER=42\nRUN_ID=run-ship-guard\nREPO=owner/repo\nMANIFEST_PATH=/tmp/manifest.json\nNO_ADMIN_FALLBACK=true\nNO_LOGS_COMMIT=true\n' >"$IMPL_TMP/ship-pr-state.sh"
printf 'export CLAUDE_PLUGIN_ROOT=%s\n' "$REPO_ROOT" >"$IMPL_TMP/plugin-root.env"
printf 'session-id\n' >"$IMPL_TMP/session-id"
cat >"$IMPL_TMP/larch-run.sh" <<EOF_RUN
#!/usr/bin/env bash
set -euo pipefail
case "\$1" in
  skills/implement/scripts/step-8-python-guard.sh) printf '%s\n' guard >> "$TMP_ROOT/order.txt"; exit 0 ;;
  *) exec bash "$REPO_ROOT/\$1" "\${@:2}" ;;
esac
EOF_RUN
chmod +x "$IMPL_TMP/larch-run.sh"

REAL_PYTHON=$(command -v python3)
STUB_BIN="$TMP_ROOT/bin"
mkdir -p "$STUB_BIN"
cat >"$STUB_BIN/python3" <<EOF_STUB
#!/usr/bin/env bash
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "bgjob" ] && [ "\$3" = "start" ]; then
  printf '%s\n' "\$@" > "$TMP_ROOT/bgjob-start-argv.txt"
  if [ -s "$IMPL_TMP/bgjob/implement-step8-ship.merge.env" ]; then printf '%s\n' merge-not-empty > "$TMP_ROOT/merge-not-empty.txt"; fi
  if [ -e "$IMPL_TMP/.step-8-ship-handoff.rc" ] || [ -e "$IMPL_TMP/.step-8-ship-handoff.json" ]; then printf '%s\n' stale-handoff > "$TMP_ROOT/stale-handoff.txt"; fi
  printf '%s\n' 'BGJOB_STATUS=STARTED STEP=implement-step8-ship PGID=12345'
  exit 0
fi
exec "$REAL_PYTHON" "\$@"
EOF_STUB
chmod +x "$STUB_BIN/python3"
printf 'old\n' >"$IMPL_TMP/bgjob/implement-step8-ship.merge.env"
printf 'stale\n' >"$IMPL_TMP/.step-8-ship-handoff.rc"
printf '{"outcome":"STALE"}\n' >"$IMPL_TMP/.step-8-ship-handoff.json"
set +e
OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" 2>"$TMP_ROOT/launch-stderr.txt")
RC=$?
set -e
assert_rc "$RC" 0 'dynamic: foreground launcher exits 0 on bgjob start'
if [ "$OUT" = 'BGJOB_STATUS=STARTED STEP=implement-step8-ship PGID=12345' ]; then pass 'dynamic: foreground launcher stdout is exact bgjob start line'; else fail "dynamic: foreground launcher stdout exact (got $OUT)"; fi
assert_contains $'--step\nimplement-step8-ship' "$(cat "$TMP_ROOT/bgjob-start-argv.txt")" 'dynamic: bgjob start step forwarded'
assert_contains '--merge-result-env' "$(cat "$TMP_ROOT/bgjob-start-argv.txt")" 'dynamic: bgjob start merge-result env forwarded'
assert_contains '--bgjob-child' "$(cat "$TMP_ROOT/bgjob-start-argv.txt")" 'dynamic: bgjob child argv forwarded'
if [ ! -e "$TMP_ROOT/merge-not-empty.txt" ]; then pass 'dynamic: merge-result env truncated before bgjob start'; else fail 'dynamic: merge-result env truncated before bgjob start'; fi
if [ ! -e "$TMP_ROOT/stale-handoff.txt" ]; then pass 'dynamic: stale handoff cleared before bgjob start'; else fail 'dynamic: stale handoff cleared before bgjob start'; fi

cat >"$STUB_BIN/python3" <<EOF_REJOIN
#!/usr/bin/env bash
if [ "\$#" -eq 0 ]; then
  cat >/dev/null
  printf '%s\n' live
  exit 0
fi
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "bgjob" ] && [ "\$3" = "wait" ]; then
  printf '%s\n' "\$@" > "$TMP_ROOT/bgjob-wait-argv.txt"
  printf '%s\n' 'BGJOB_STATUS=WAIT'
  printf '%s\n' 'ELAPSED_S=0'
  exit 0
fi
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "bgjob" ] && [ "\$3" = "start" ]; then
  printf '%s\n' unexpected-start > "$TMP_ROOT/unexpected-rejoin-start.txt"
  exit 0
fi
exec "$REAL_PYTHON" "\$@"
EOF_REJOIN
chmod +x "$STUB_BIN/python3"
set +e
REJOIN_OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" 2>"$TMP_ROOT/rejoin-stderr.txt")
REJOIN_RC=$?
set -e
assert_rc "$REJOIN_RC" 0 'dynamic: live registry rejoin exits with bgjob wait rc'
assert_contains 'BGJOB_STATUS=WAIT' "$REJOIN_OUT" 'dynamic: live registry rejoin emits wait envelope'
assert_contains $'--step\nimplement-step8-ship' "$(cat "$TMP_ROOT/bgjob-wait-argv.txt")" 'dynamic: live registry rejoin waits on Step 8 slug'
if [ ! -e "$TMP_ROOT/unexpected-rejoin-start.txt" ]; then pass 'dynamic: live registry rejoin refuses second bgjob start'; else fail 'dynamic: live registry rejoin refuses second bgjob start'; fi

cat >"$STUB_BIN/python3" <<EOF_CHILD
#!/usr/bin/env bash
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "implement" ] && [ "\$3" = "clone-tag" ]; then
  printf '%s\n' 'CLONE_TAG_FULL=stub'
  printf '%s\n' 'EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-stub-'
  exit 0
fi
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "git" ] && [ "\$3" = "phantom-probe" ]; then
  printf '%s\n' phantom >> "$TMP_ROOT/order.txt"
  printf '%s\n' 'PHANTOM_STATUS=clean'
  exit 0
fi
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "ship" ] && [ "\$3" = "pr" ]; then
  printf '%s\n' driver >> "$TMP_ROOT/order.txt"
  printf '%s\n' "\$@" > "$TMP_ROOT/ship-argv.txt"
  printf '%s\n' '{"outcome":"NEEDS_USER_INPUT","needs_user_reason":"oos-filing"}'
  exit 3
fi
exec "$REAL_PYTHON" "\$@"
EOF_CHILD
chmod +x "$STUB_BIN/python3"
MERGE_ENV="$IMPL_TMP/bgjob/implement-step8-ship.merge.env"
: >"$TMP_ROOT/order.txt"
set +e
CHILD_OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" --bgjob-child --merge-result-env "$MERGE_ENV" 2>"$TMP_ROOT/child-stderr.txt")
CHILD_RC=$?
set -e
assert_rc "$CHILD_RC" 0 'dynamic: child exits 0 after persisting non-zero driver rc'
assert_contains $'guard\nphantom\ndriver' "$(cat "$TMP_ROOT/order.txt")" 'dynamic: child runs guard then phantom then driver'
assert_contains 'PHANTOM_STATUS=clean' "$(cat "$TMP_ROOT/child-stderr.txt")" 'dynamic: phantom stdout redirected to stderr'
assert_contains '"needs_user_reason":"oos-filing"' "$CHILD_OUT" 'dynamic: child captures and forwards driver JSON when invoked directly'
assert_contains '--branch' "$(cat "$TMP_ROOT/ship-argv.txt")" 'dynamic: child forwards branch flag'
assert_contains 'test-branch' "$(cat "$TMP_ROOT/ship-argv.txt")" 'dynamic: child forwards branch value'
assert_contains '3' "$(cat "$IMPL_TMP/.step-8-ship-handoff.rc")" 'dynamic: handoff rc stores driver rc 3'
assert_contains '"needs_user_reason":"oos-filing"' "$(cat "$IMPL_TMP/.step-8-ship-handoff.json")" 'dynamic: driver JSON sidecar written after drain'
assert_contains 'STEP8_HANDOFF_RC=3' "$(cat "$MERGE_ENV")" 'dynamic: merge result records driver rc 3'
assert_contains 'STEP8_HANDOFF_JSON_PRESENT=true' "$(cat "$MERGE_ENV")" 'dynamic: merge result records json presence'

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

printf '{"outcome":"STALE"}\n' >"$IMPL_TMP/.step-8-ship-handoff.json"
printf 'RUN_ID=run-ship-guard\nREPO=owner/repo\n' >"$IMPL_TMP/ship-pr-state.sh"
set +e
SETUP_OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" --bgjob-child --merge-result-env "$MERGE_ENV" 2>"$TMP_ROOT/setup-stderr.txt")
SETUP_RC=$?
set -e
assert_rc "$SETUP_RC" 2 'child: require_value setup failure exits 2'
assert_contains '2' "$(cat "$IMPL_TMP/.step-8-ship-handoff.rc")" 'child: setup failure handoff rc written'
if [ ! -e "$IMPL_TMP/.step-8-ship-handoff.json" ]; then pass 'child: setup failure unlinks stale handoff json'; else fail 'child: setup failure unlinks stale handoff json'; fi
if [ -z "$SETUP_OUT" ]; then pass 'child: setup failure stdout empty'; else fail 'child: setup failure stdout empty'; fi

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
if [ -z "$GUARD_OUT" ]; then pass 'guard: new python stdout empty'; else fail 'guard: new python stdout empty'; fi

CLONE_OUT=$(mkdir -p "$TMP_ROOT/repo with spaces" && cd "$TMP_ROOT/repo with spaces" && CLONE_TAG='' "$REAL_PYTHON" "$REPO_ROOT/python/cli.py" implement clone-tag)
assert_contains 'EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-repo_with_spaces-' "$CLONE_OUT" 'clone CLI: derives sanitized prefix from PWD'

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
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "implement" ] && [ "\$3" = "clone-tag" ]; then
  printf '%s\n' 'CLONE_TAG_FULL=seedstub'
  printf '%s\n' 'EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-seedstub-'
  exit 0
fi
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
assert_contains 'claude-implement-seedstub-' "$seed_argv" 'seeder: clone-tag CLI prefix forwarded'

if [ "$FAIL" -eq 0 ]; then
  printf 'PASS: test-step-8-ship.sh (%d assertions)\n' "$PASS"
  exit 0
fi
printf 'FAIL: test-step-8-ship.sh (%d passed, %d failed)\n' "$PASS" "$FAIL" >&2
exit 1
