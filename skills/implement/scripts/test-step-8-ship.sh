#!/usr/bin/env bash
# test-step-8-ship.sh — offline harness for Step 8 ship wrappers.

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
assert_contains 'python/cli.py" implement clone-tag' "$helper_text" 'static: clone-tag CLI invoked'
# shellcheck disable=SC2016
assert_contains 'clone_tag_env=$(python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement clone-tag) || exit $?' "$helper_text" 'static: clone-tag capture fails closed'
# shellcheck disable=SC2016
assert_contains 'eval "$clone_tag_env"' "$helper_text" 'static: clone-tag env evaluated after successful capture'
assert_contains 'step-8-python-guard.sh' "$helper_text" 'static: shared python guard invoked'
guard_line=$(grep -n 'step-8-python-guard.sh' "$HELPER" | head -n 1 | cut -d: -f1)
clone_line=$(grep -n 'implement clone-tag' "$HELPER" | head -n 1 | cut -d: -f1)
if [ -n "$guard_line" ] && [ -n "$clone_line" ] && [ "$guard_line" -lt "$clone_line" ]; then
  pass 'static: python guard runs before clone-tag CLI'
else
  fail 'static: python guard runs before clone-tag CLI'
fi
# shellcheck disable=SC2016
assert_contains 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" git phantom-probe --step 8-pre-ship >&2' "$helper_text" 'static: bundled phantom probe redirects stdout'
assert_not_contains 'sys.version_info >= (3, 11)' "$helper_text" 'static: inline python version guard absent from ship wrapper'
# shellcheck disable=SC2016
assert_not_contains 'claude-implement-${CLONE_TAG_FULL}-' "$helper_text" 'static: inline tmpdir prefix absent from ship wrapper'
# shellcheck disable=SC2016
assert_contains 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr' "$helper_text" 'static: python ship CLI invoked'
# shellcheck disable=SC2016
assert_contains '--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"' "$helper_text" 'static: state file forwarded'
# shellcheck disable=SC2016
assert_contains '--expected-tmpdir-basename-prefix "$EXPECTED_TMPDIR_BASENAME_PREFIX"' "$helper_text" 'static: shared prefix forwarded'
# shellcheck disable=SC2016
assert_contains ': >"$HANDOFF_CAPTURE"' "$helper_text" 'static: capture truncated at wrapper entry'
assert_contains 'trap persist_handoff EXIT' "$helper_text" 'static: EXIT trap persists handoff'
# shellcheck disable=SC2016
assert_contains '.bg-wait-active' "$helper_text" 'static: wrapper writes bg-wait marker'
assert_contains 'STEP=implement-step8-ship' "$helper_text" 'static: marker names implement-step8-ship'
assert_contains 'TIMEOUT_S=21600' "$helper_text" 'static: marker pins Step 8 timeout'
assert_contains 'no-progress-turns.count' "$helper_text" 'static: wrapper clears no-progress counter'
assert_contains 'no-progress-circuit-breaker-armed' "$helper_text" 'static: wrapper clears no-progress breaker'
assert_contains 'bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count' "$helper_text" 'static: wrapper clears Step 8 rc probe clamp counter'
# shellcheck disable=SC2016
assert_contains 'rm -f "$HANDOFF_RC" "$HANDOFF_JSON"' "$helper_text" 'static: wrapper removes stale handoff sidecars at entry'
# shellcheck disable=SC2016
assert_contains 'rm -f "$IMPLEMENT_TMPDIR/.bg-wait-active"' "$helper_text" 'static: EXIT trap removes bg-wait marker'
# shellcheck disable=SC2016
assert_contains 'tee -a "$HANDOFF_CAPTURE"' "$helper_text" 'static: stdout captured through tee'
# shellcheck disable=SC2016
assert_contains 'rm -f "$HANDOFF_JSON"' "$helper_text" 'static: stale json unlinked on rc-only exit'
rc_write_line=$(grep -n 'printf.*HANDOFF_RC' "$HELPER" | head -n 1 | cut -d: -f1)
json_write_line=$(grep -n 'HANDOFF_JSON' "$HELPER" | grep 'printf' | head -n 1 | cut -d: -f1)
marker_remove_line=$(grep -n 'rm -f.*bg-wait-active' "$HELPER" | head -n 1 | cut -d: -f1)
if [ -n "$rc_write_line" ] && [ -n "$json_write_line" ] && [ -n "$marker_remove_line" ] && [ "$rc_write_line" -lt "$marker_remove_line" ] && [ "$json_write_line" -lt "$marker_remove_line" ]; then
  pass 'static: persist_handoff writes rc/json before marker removal'
else
  fail 'static: persist_handoff writes rc/json before marker removal'
fi

seeder_text=$(cat "$SEEDER")
assert_contains 'ship seed-initial-state' "$seeder_text" 'static: seeder wrapper delegates to Python seeder'
# shellcheck disable=SC2016
assert_contains 'session read-key --file "$file"' "$seeder_text" 'static: seeder reads session keys through python cli'
assert_not_contains 'read-session-env-key.sh' "$seeder_text" 'static: retired session reader absent'
assert_contains 'python/cli.py" implement clone-tag' "$seeder_text" 'static: seeder invokes clone-tag CLI'
# shellcheck disable=SC2016
assert_contains 'clone_tag_env=$(python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" implement clone-tag) || exit $?' "$seeder_text" 'static: seeder clone-tag capture fails closed'
# shellcheck disable=SC2016
assert_contains ': "${EXPECTED_TMPDIR_BASENAME_PREFIX:?}"' "$seeder_text" 'static: seeder requires shared prefix'

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
  *) exec bash "$REPO_ROOT/\$1" "\${@:2}" ;;
esac
EOF_RUN
chmod +x "$IMPL_TMP/larch-run.sh"

REAL_PYTHON=$(command -v python3)
STUB_BIN="$TMP_ROOT/bin"
mkdir -p "$STUB_BIN"
cat >"$STUB_BIN/python3" <<EOF_STUB
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
  if [ -f "$IMPL_TMP/.bg-wait-active" ]; then cp "$IMPL_TMP/.bg-wait-active" "$TMP_ROOT/marker-during-driver.txt"; fi
  for f in no-progress-turns.count no-progress-circuit-breaker-armed bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count .step-8-ship-handoff.rc .step-8-ship-handoff.json; do
    if [ -e "$IMPL_TMP/\$f" ]; then printf '%s\n' "\$f" >> "$TMP_ROOT/stale-seen-during-driver.txt"; fi
  done
  printf '%s\n' '{"outcome":"OK","detail":"stub"}'
  exit 0
fi
exec "$REAL_PYTHON" "\$@"
EOF_STUB
chmod +x "$STUB_BIN/python3"
: >"$IMPL_TMP/no-progress-turns.count"
: >"$IMPL_TMP/no-progress-circuit-breaker-armed"
printf '99\n' >"$IMPL_TMP/bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count"
printf 'stale-rc\n' >"$IMPL_TMP/.step-8-ship-handoff.rc"
printf '{"outcome":"STALE"}\n' >"$IMPL_TMP/.step-8-ship-handoff.json"

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
assert_contains 'claude-implement-stub-' "$(cat "$TMP_ROOT/ship-argv.txt")" 'dynamic: forwards clone-tag CLI prefix value'
assert_contains '0' "$(cat "$IMPL_TMP/.step-8-ship-handoff.rc")" 'dynamic: handoff rc written on success'
assert_contains '"outcome":"OK"' "$(cat "$IMPL_TMP/.step-8-ship-handoff.json")" 'dynamic: driver JSON sidecar written after drain'
assert_contains 'STEP=implement-step8-ship' "$(cat "$TMP_ROOT/marker-during-driver.txt")" 'dynamic: marker visible while driver runs with Step 8 step'
assert_contains 'TIMEOUT_S=21600' "$(cat "$TMP_ROOT/marker-during-driver.txt")" 'dynamic: marker visible while driver runs with timeout'
if [ ! -s "$TMP_ROOT/stale-seen-during-driver.txt" ]; then
  pass 'dynamic: stale handoff, no-progress, and probe counter files cleared before driver'
else
  fail "dynamic: stale files seen by driver: $(cat "$TMP_ROOT/stale-seen-during-driver.txt")"
fi
if [ ! -e "$IMPL_TMP/.bg-wait-active" ]; then
  pass 'dynamic: bg-wait marker absent after success'
else
  fail 'dynamic: bg-wait marker absent after success'
fi

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

cat >"$IMPL_TMP/larch-run.sh" <<EOF_STALE_RUN
#!/usr/bin/env bash
set -euo pipefail
case "\$1" in
  skills/implement/scripts/step-8-python-guard.sh) exec bash "$GUARD" ;;
  *) exec bash "$REPO_ROOT/\$1" "\${@:2}" ;;
esac
EOF_STALE_RUN
chmod +x "$IMPL_TMP/larch-run.sh"
: >"$TMP_ROOT/order.txt"
set +e
STALE_OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" 2>"$TMP_ROOT/stale-wrapper-stderr.txt")
STALE_RC=$?
set -e
assert_rc "$STALE_RC" 4 'wrapper: stale python exits 4 before clone-tag'
assert_contains '"outcome":"STALLED"' "$STALE_OUT" 'wrapper: stale python emits STALLED JSON'
assert_not_contains 'driver' "$(cat "$TMP_ROOT/order.txt" 2>/dev/null || true)" 'wrapper: stale python skips ship driver'
assert_contains '4' "$(cat "$IMPL_TMP/.step-8-ship-handoff.rc")" 'wrapper: stale python handoff rc written'
assert_contains '"outcome":"STALLED"' "$(cat "$IMPL_TMP/.step-8-ship-handoff.json")" 'wrapper: stale python JSON sidecar written'
if [ ! -e "$IMPL_TMP/.bg-wait-active" ]; then
  pass 'wrapper: stale python removes bg-wait marker'
else
  fail 'wrapper: stale python removes bg-wait marker'
fi

printf '%s\n' '{"outcome":"STALE"}' >"$IMPL_TMP/.step-8-ship-handoff.json"
printf 'RUN_ID=run-ship-guard\nREPO=owner/repo\n' >"$IMPL_TMP/ship-pr-state.sh"
set +e
SETUP_OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" 2>"$TMP_ROOT/setup-stderr.txt")
SETUP_RC=$?
set -e
assert_rc "$SETUP_RC" 2 'wrapper: require_value setup failure exits 2'
assert_contains '2' "$(cat "$IMPL_TMP/.step-8-ship-handoff.rc")" 'wrapper: setup failure handoff rc written'
if [ ! -e "$IMPL_TMP/.step-8-ship-handoff.json" ]; then
  pass 'wrapper: setup failure unlinks stale handoff json'
else
  fail 'wrapper: setup failure unlinks stale handoff json'
fi
if [ -z "$SETUP_OUT" ]; then
  pass 'wrapper: setup failure stdout empty'
else
  fail 'wrapper: setup failure stdout empty'
fi
if [ ! -e "$IMPL_TMP/.bg-wait-active" ]; then
  pass 'wrapper: setup failure removes bg-wait marker'
else
  fail 'wrapper: setup failure removes bg-wait marker'
fi

printf 'BRANCH_NAME=test-branch\nISSUE_NUMBER=42\nRUN_ID=run-ship-guard\nREPO=owner/repo\nMANIFEST_PATH=/tmp/manifest.json\n' >"$IMPL_TMP/ship-pr-state.sh"
cat >"$IMPL_TMP/larch-run.sh" <<EOF_FAIL_RUN
#!/usr/bin/env bash
set -euo pipefail
case "\$1" in
  skills/implement/scripts/step-8-python-guard.sh) exit 0 ;;
  *) exec bash "$REPO_ROOT/\$1" "\${@:2}" ;;
esac
EOF_FAIL_RUN
chmod +x "$IMPL_TMP/larch-run.sh"
cat >"$STUB_BIN/python3" <<EOF_FAIL_SHIP
#!/usr/bin/env bash
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "implement" ] && [ "\$3" = "clone-tag" ]; then
  printf '%s\n' 'CLONE_TAG_FULL=stub'
  printf '%s\n' 'EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-stub-'
  exit 0
fi
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "git" ] && [ "\$3" = "phantom-probe" ]; then exit 0; fi
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "ship" ] && [ "\$3" = "pr" ]; then
  [ -f "$IMPL_TMP/.bg-wait-active" ] && printf '%s\n' marker-present >"$TMP_ROOT/fail-marker-seen.txt"
  printf '%s\n' '{"outcome":"INTERNAL_ERROR","detail":"fail-stub"}'
  exit 1
fi
exec "$REAL_PYTHON" "\$@"
EOF_FAIL_SHIP
chmod +x "$STUB_BIN/python3"
set +e
FAIL_OUT=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" 2>"$TMP_ROOT/fail-stderr.txt")
FAIL_RC=$?
set -e
assert_rc "$FAIL_RC" 1 'wrapper: failing ship driver exits 1'
assert_contains '"outcome":"INTERNAL_ERROR"' "$FAIL_OUT" 'wrapper: failing ship forwards failure JSON stdout'
assert_contains 'marker-present' "$(cat "$TMP_ROOT/fail-marker-seen.txt")" 'wrapper: failing ship driver runs after marker armed'
assert_contains '1' "$(cat "$IMPL_TMP/.step-8-ship-handoff.rc")" 'wrapper: failing ship handoff rc written'
assert_contains '"outcome":"INTERNAL_ERROR"' "$(cat "$IMPL_TMP/.step-8-ship-handoff.json")" 'wrapper: failing ship JSON sidecar written'
if [ ! -e "$IMPL_TMP/.bg-wait-active" ]; then
  pass 'wrapper: failing ship removes bg-wait marker'
else
  fail 'wrapper: failing ship removes bg-wait marker'
fi

printf 'old\n' >"$IMPL_TMP/.step-8-ship-handoff.rc"
printf '{"outcome":"OLD"}\n' >"$IMPL_TMP/.step-8-ship-handoff.json"
printf '99\n' >"$IMPL_TMP/bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count"
rm -f "$IMPL_TMP/.step-8-ship-handoff.rc" "$IMPL_TMP/.step-8-ship-handoff.json" 2>/dev/null || true
if [ ! -e "$IMPL_TMP/.step-8-ship-handoff.rc" ] && [ ! -e "$IMPL_TMP/.step-8-ship-handoff.json" ]; then
  pass 'relaunch regression: foreground pre-launch clear removes stale handoff sidecars'
else
  fail 'relaunch regression: foreground pre-launch clear removes stale handoff sidecars'
fi
if ! test -f "$IMPL_TMP/.step-8-ship-handoff.rc"; then
  pass 'relaunch regression: rc probe absent after foreground pre-launch clear'
else
  fail 'relaunch regression: rc probe absent after foreground pre-launch clear'
fi
cat >"$IMPL_TMP/larch-run.sh" <<EOF_RELAUNCH_RUN
#!/usr/bin/env bash
set -euo pipefail
case "\$1" in
  skills/implement/scripts/step-8-python-guard.sh) printf '%s\n' guard >> "$TMP_ROOT/relaunch-order.txt"; exit 0 ;;
  *) exec bash "$REPO_ROOT/\$1" "\${@:2}" ;;
esac
EOF_RELAUNCH_RUN
chmod +x "$IMPL_TMP/larch-run.sh"
cat >"$STUB_BIN/python3" <<EOF_RELAUNCH_STUB
#!/usr/bin/env bash
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "implement" ] && [ "\$3" = "clone-tag" ]; then
  printf '%s\n' 'CLONE_TAG_FULL=stub'
  printf '%s\n' 'EXPECTED_TMPDIR_BASENAME_PREFIX=claude-implement-stub-'
  exit 0
fi
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "git" ] && [ "\$3" = "phantom-probe" ]; then
  printf '%s\n' phantom >> "$TMP_ROOT/relaunch-order.txt"
  exit 0
fi
if [ "\$1" = "$REPO_ROOT/python/cli.py" ] && [ "\$2" = "ship" ] && [ "\$3" = "pr" ]; then
  printf '%s\n' driver >> "$TMP_ROOT/relaunch-order.txt"
  if [ -f "$IMPL_TMP/.bg-wait-active" ]; then cp "$IMPL_TMP/.bg-wait-active" "$TMP_ROOT/relaunch-marker-during-driver.txt"; fi
  for f in .step-8-ship-handoff.rc .step-8-ship-handoff.json bg-poll-guard-probe-denials.step-8-ship-handoff.rc.count; do
    if [ -e "$IMPL_TMP/\$f" ]; then printf '%s\n' "\$f" >> "$TMP_ROOT/relaunch-stale-seen-during-driver.txt"; fi
  done
  printf '%s\n' '{"outcome":"OK","detail":"relaunch-stub"}'
  exit 0
fi
exec "$REAL_PYTHON" "\$@"
EOF_RELAUNCH_STUB
chmod +x "$STUB_BIN/python3"
: >"$TMP_ROOT/relaunch-order.txt"
: >"$TMP_ROOT/relaunch-stale-seen-during-driver.txt"
printf 'stale-relaunch-rc\n' >"$IMPL_TMP/.step-8-ship-handoff.rc"
printf '{"outcome":"STALE_RELAUNCH"}\n' >"$IMPL_TMP/.step-8-ship-handoff.json"
rm -f "$IMPL_TMP/.step-8-ship-handoff.rc" "$IMPL_TMP/.step-8-ship-handoff.json" 2>/dev/null || true
if test -f "$IMPL_TMP/.step-8-ship-handoff.rc"; then
  fail 'relaunch regression: stale rc must not survive foreground pre-launch clear before wrapper'
else
  pass 'relaunch regression: stale rc absent before wrapper relaunch'
fi
set +e
_relaunch_out=$(PATH="$STUB_BIN:$PATH" IMPLEMENT_TMPDIR="$IMPL_TMP" CLAUDE_PLUGIN_ROOT="$REPO_ROOT" bash "$HELPER" 2>"$TMP_ROOT/relaunch-stderr.txt")
RELAUNCH_RC=$?
set -e
assert_rc "$RELAUNCH_RC" 0 'relaunch regression: wrapper exits 0 on relaunch'
assert_contains $'guard\nphantom\ndriver' "$(cat "$TMP_ROOT/relaunch-order.txt")" 'relaunch regression: wrapper runs guard then driver on relaunch'
assert_contains 'STEP=implement-step8-ship' "$(cat "$TMP_ROOT/relaunch-marker-during-driver.txt")" 'relaunch regression: marker armed before driver on relaunch'
if [ ! -s "$TMP_ROOT/relaunch-stale-seen-during-driver.txt" ]; then
  pass 'relaunch regression: stale rc/json cleared before driver on relaunch'
else
  fail "relaunch regression: stale sidecars seen by driver: $(cat "$TMP_ROOT/relaunch-stale-seen-during-driver.txt")"
fi
assert_contains '0' "$(cat "$IMPL_TMP/.step-8-ship-handoff.rc")" 'relaunch regression: fresh handoff rc written after relaunch'
assert_contains '"outcome":"OK"' "$(cat "$IMPL_TMP/.step-8-ship-handoff.json")" 'relaunch regression: fresh handoff json written after relaunch'
if [ ! -e "$IMPL_TMP/.bg-wait-active" ]; then
  pass 'relaunch regression: bg-wait marker removed after relaunch completes'
else
  fail 'relaunch regression: bg-wait marker removed after relaunch completes'
fi

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
