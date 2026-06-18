#!/usr/bin/env bash
# test-design-step3-review.sh — static Step 3 reporting contract checks.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
MODULE="$ROOT/python/plan_review.py"
LOOP="$ROOT/skills/design/scripts/review-design-step3-loop.sh"
WRAPPER="$ROOT/skills/design/scripts/design-step3-review.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

make_fake_step3_plugin() {
  local dir="$1" run_body="$2"
  mkdir -p "$dir/scripts" "$dir/skills/design/scripts" "$dir/python"
  ln -sf "$ROOT/scripts/read-result-env.sh" "$dir/scripts/read-result-env.sh"
  ln -sf "$ROOT/scripts/lib-quiet.sh" "$dir/scripts/lib-quiet.sh"
  cat >"$dir/skills/design/scripts/plan-review-loop-stub.sh" <<EOFSTUB
#!/usr/bin/env bash
set -euo pipefail
$run_body
EOFSTUB
  chmod +x "$dir/skills/design/scripts/plan-review-loop-stub.sh"
  cat >"$dir/python/cli.py" <<'CLIPY'
#!/usr/bin/env python3
import subprocess, sys, os
if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] == "run":
    run_sh = os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", ""), "skills", "design", "scripts", "plan-review-loop-stub.sh")
    sys.exit(subprocess.call(["/bin/bash", run_sh]))
real_cli = os.path.join(os.environ.get("LARCH_TEST_REAL_REPO_ROOT", ""), "python", "cli.py")
if real_cli and os.path.isfile(real_cli):
    sys.exit(subprocess.call([sys.executable, real_cli, *sys.argv[1:]]))
sys.exit(0)
CLIPY
  chmod +x "$dir/python/cli.py"
}

grep -Fq 'step3_stage_postplan_failed' "$LOOP" || fail 'postplan-failed staging helper missing'
grep -Fq -- '--outcome failed-postplan' "$LOOP" || fail 'failed-postplan outcome not staged'
# shellcheck disable=SC2016
( command grep -Fq 'record-escalation' "$LOOP" ) || fail 'record-escalation call missing'
# shellcheck disable=SC2016
( command grep -Fq -- '--site "$site"' "$LOOP" ) || fail 'record-escalation --site missing'
# shellcheck disable=SC2016
( command grep -Fq -- '--trigger "$trigger"' "$LOOP" ) || fail 'record-escalation --trigger missing'
grep -Fq 'main-agent-vote-required|main-agent-apply-required|postplan-operator-required|panel-failed|tally-error|degraded-empty-collector' "$LOOP" || fail 'escalation/degradation status set missing'
python3 - "$LOOP" <<'PY' || fail 'round-start persist contract missing or misordered'
from __future__ import annotations

import sys
from pathlib import Path

body = Path(sys.argv[1]).read_text(encoding="utf-8")
helper = body[body.index("step3_loop_persist_round_start_s() {"):body.index("step3_loop_phase_file() {")]
required = [
    'python3 "$PLUGIN_ROOT/python/cli.py" plan-review persist-round-start-s',
    '--design-tmpdir "$DESIGN_TMPDIR" --round-num "$round_num" --start-s "$start_s"',
]
missing = [item for item in required if item not in helper]
if missing:
    raise SystemExit(f"missing helper substrings: {missing}")
round_start_idx = body.index('round_start_s="$(step3_loop_now_s)"')
persist_idx = body.index('step3_loop_persist_round_start_s "$round_num" "$round_start_s"', round_start_idx)
body_idx = body.index('run_step3_round_body', persist_idx)
if not (round_start_idx < persist_idx < body_idx):
    raise SystemExit("persist call must be between round_start_s capture and run_step3_round_body")
PY
pass 'Step 3 loop persists round-start-s before round body with symlink guards'
for status in panel-failed tally-error degraded-empty-collector; do
  grep -Fq "$status" "$MODULE" || fail "$status missing"
done
if grep -Fq 'failed-judge-panel' "$MODULE"; then
  fail 'Step 3 must not handle Step 2b.5 failed-judge-panel retry exhaustion'
fi
if grep -Fq 'render-final-summary.sh' "$WRAPPER"; then
  fail 'design-step3-review.sh must not render final summary'
fi
if grep -Fq '**⚠ Step 3: postplan failed' "$WRAPPER"; then
  fail 'postplan-failed stdout must remain KV-only'
fi
grep -Fq 'SUMMARY_OUTCOME=failed-postplan' "$WRAPPER" || fail 'postplan-failed summary KV missing'
grep -Fq 'SUMMARY_OUTCOME=failed-judge-panel' "$WRAPPER" || fail 'panel-init-failed summary KV missing'
grep -Fq 'step3_loop_write_terminal_step3' "$LOOP" || fail 'Step 3 loop terminal sentinel helper missing'
grep -Fq '.step3-terminal-persisted-this-run' "$LOOP" || fail 'Step 3 loop persist sidecar missing'
grep -Fq '.step3-terminal-persisted-this-run' "$WRAPPER" || fail 'Step 3 wrapper must key terminal trap fallback and step-3 guarantee on current-pass sidecar'
# shellcheck disable=SC2016 # literal $DESIGN_TMPDIR must match wrapper source text.
grep -Fq 'rm -f "$DESIGN_TMPDIR/.step3-review-result.env" "$DESIGN_TMPDIR/.completed/step-3"' "$WRAPPER" || fail 'Step 3 wrapper must clear stale result env and step-3 at non-resume entry'
# shellcheck disable=SC2016 # literal $DESIGN_TMPDIR must match wrapper source text.
grep -Fq 'rm -f "$DESIGN_TMPDIR/.completed/step-3"' "$WRAPPER" || fail 'Step 3 wrapper must clear stale step-3 on mid-loop resume entry'

D_STEP3=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-stage.XXXXXX")
trap 'rm -rf "$D_STEP3"' EXIT
STAGE_HELPER="$ROOT/skills/design/scripts/design-stage-terminal-state.sh"
env -u CLAUDE_PLUGIN_ROOT "$STAGE_HELPER" --design-tmpdir "$D_STEP3" \
  --outcome failed-postplan --step postplan --phase postplan --site step3-review \
  --trigger postplan-failed --bail-reason postplan-failed --exit-code 10 \
  --source-script design-step3-review --summary-outcome failed-postplan >/dev/null
[ -f "$D_STEP3/design-failure-terminal-state.env" ] || fail 'postplan-failed staging must write terminal state'
grep -Fxq 'FAILURE_OUTCOME=failed-postplan' "$D_STEP3/design-failure-terminal-state.env" || fail 'postplan terminal outcome missing'
pass 'Step 3 postplan-failed stages terminal state at runtime'

assert_escalation_recorded() {
  local status="$1" expected_phase="$2"
  local dir
  dir=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-escalation-${status}.XXXXXX")
  python3 "$ROOT/python/cli.py" plan-review run --design-tmpdir "$dir" --record-report-evidence "$status" >/dev/null
  [ -s "$dir/design-failure-escalation-ledger.tsv" ] || fail "${status} must record escalation ledger row"
  grep -Fq "trigger=${status}" "$dir/design-failure-escalation-ledger.tsv" || fail "${status} ledger trigger missing"
  grep -Fq "phase=${expected_phase}" "$dir/design-failure-escalation-ledger.tsv" || fail "${status} ledger phase=${expected_phase} missing"
  [ ! -f "$dir/design-failure-terminal-state.env" ] || fail "${status} must not stage terminal state"
  rm -rf "$dir"
}

for status in main-agent-vote-required main-agent-apply-required panel-failed panel-init-failed degraded-empty-collector tally-error; do
  assert_escalation_recorded "$status" validation
done
assert_escalation_recorded postplan-operator-required postplan
pass 'Step 3 main-agent and degradation statuses record escalation evidence'

D_ROUND_START=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-round-start.XXXXXX")
cat >"$D_ROUND_START/continuation.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'PLAN_REVIEW_CONTINUE=false' 'ACCEPTED_COUNT=0' 'DEGRADED_PANEL=0'
SH
chmod +x "$D_ROUND_START/continuation.sh"
cat >"$D_ROUND_START/source-live-loop.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
export DESIGN_TMPDIR="$1"
export PLUGIN_ROOT="$2"
export STARTING_ROUND=1
export RUN_STEP3_CONTINUATION_SH="$DESIGN_TMPDIR/continuation.sh"
emit() { printf '%s\n' "$*"; }
emit_kv() { printf '%s=%s\n' "$1" "$2"; }
larch_err() { printf '%s\n' "$*" >&2; }
phase_driver_write_result_env() {
  local result_env="$1"
  shift
  printf '%s\n' "$@" >"$result_env"
}
run_step3_round_body() {
  : >"$DESIGN_TMPDIR/body-entered"
  local waited=0
  while [[ ! -f "$DESIGN_TMPDIR/release-body" && "$waited" -lt 50 ]]; do
    sleep 0.1
    waited=$((waited + 1))
  done
  LOOP_STATUS=complete
  STEP3_REVIEW_ROUND_NUM=1
  TALLY_PLAN_REVIEW_STATUS=ok
}
# shellcheck source=/dev/null
source "$PLUGIN_ROOT/skills/design/scripts/review-design-step3-loop.sh"
run_design_step3_loop
SH
chmod +x "$D_ROUND_START/source-live-loop.sh"
"$D_ROUND_START/source-live-loop.sh" "$D_ROUND_START" "$ROOT" >"$D_ROUND_START/stdout.log" 2>"$D_ROUND_START/stderr.log" &
round_start_pid=$!
release_round_start_stub() {
  touch "$D_ROUND_START/release-body" 2>/dev/null || true
}
wait_round_start_pid_bounded() {
  local waited=0
  while kill -0 "$round_start_pid" 2>/dev/null && [[ "$waited" -lt 50 ]]; do
    sleep 0.1
    waited=$((waited + 1))
  done
  if kill -0 "$round_start_pid" 2>/dev/null; then
    kill "$round_start_pid" 2>/dev/null || true
    waited=0
    while kill -0 "$round_start_pid" 2>/dev/null && [[ "$waited" -lt 50 ]]; do
      sleep 0.1
      waited=$((waited + 1))
    done
    kill -9 "$round_start_pid" 2>/dev/null || true
    wait "$round_start_pid" 2>/dev/null || true
    return 1
  fi
  wait "$round_start_pid"
}
cleanup_round_start_harness() {
  release_round_start_stub
  if kill -0 "$round_start_pid" 2>/dev/null; then
    kill "$round_start_pid" 2>/dev/null || true
    local waited=0
    while kill -0 "$round_start_pid" 2>/dev/null && [[ "$waited" -lt 50 ]]; do
      sleep 0.1
      waited=$((waited + 1))
    done
    kill -9 "$round_start_pid" 2>/dev/null || true
  fi
  wait "$round_start_pid" 2>/dev/null || true
  rm -rf "$D_ROUND_START" 2>/dev/null || true
}
trap cleanup_round_start_harness EXIT
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
  [[ -f "$D_ROUND_START/body-entered" ]] && break
  sleep 0.1
done
if [[ ! -f "$D_ROUND_START/body-entered" ]]; then
  wait_round_start_pid_bounded || true
  fail "live loop body did not start; stderr=$(cat "$D_ROUND_START/stderr.log")"
fi
[[ -f "$D_ROUND_START/plan-review/round-1/round-start-s" ]] || {
  wait_round_start_pid_bounded || true
  fail 'live loop must persist round-start-s before round body returns'
}
release_round_start_stub
wait_round_start_pid_bounded || fail "live loop round-start harness failed; stderr=$(cat "$D_ROUND_START/stderr.log")"
trap - EXIT
rm -rf "$D_ROUND_START"
pass 'Step 3 live loop creates round-start-s before the sourced round body returns'

D_PERSIST_GUARD=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-persist-guard.XXXXXX")
OUTSIDE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-persist-outside.XXXXXX")
# shellcheck disable=SC2016
cat >"$D_PERSIST_GUARD/run-persist.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
export DESIGN_TMPDIR="$1"
export PLUGIN_ROOT="$2"
# shellcheck source=/dev/null
source "$PLUGIN_ROOT/skills/design/scripts/review-design-step3-loop.sh"
step3_loop_persist_round_start_s 1 12345
SH
chmod +x "$D_PERSIST_GUARD/run-persist.sh"
ln -s "$OUTSIDE" "$D_PERSIST_GUARD/plan-review"
"$D_PERSIST_GUARD/run-persist.sh" "$D_PERSIST_GUARD" "$ROOT"
[[ ! -e "$OUTSIDE/round-1/round-start-s" ]] || fail 'persist must not follow symlinked plan-review parent'
rm "$D_PERSIST_GUARD/plan-review"
printf 'x\n' >"$D_PERSIST_GUARD/plan-review"
set +e
"$D_PERSIST_GUARD/run-persist.sh" "$D_PERSIST_GUARD" "$ROOT"
file_parent_rc=$?
set -e
[[ "$file_parent_rc" -eq 0 ]] || fail "persist must not abort when plan-review parent is a file (rc=$file_parent_rc)"
rm -rf "$D_PERSIST_GUARD" "$OUTSIDE"
pass 'Step 3 persist helper skips symlink parent and tolerates mkdir failure'

D_PERSIST_TOCTOU=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-persist-toctou.XXXXXX")
OUTSIDE_TOCTOU=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-persist-toctou-outside.XXXXXX")
mkdir -p "$D_PERSIST_TOCTOU/plan-review/round-1"
ln -s "$OUTSIDE_TOCTOU/round-start-s" "$D_PERSIST_TOCTOU/plan-review/round-1/round-start-s"
python3 "$ROOT/python/cli.py" plan-review persist-round-start-s \
  --design-tmpdir "$D_PERSIST_TOCTOU" --round-num 1 --start-s 12345
[[ ! -e "$OUTSIDE_TOCTOU/round-start-s" ]] || fail 'persist must not follow symlinked round-start-s'
rm -rf "$D_PERSIST_TOCTOU" "$OUTSIDE_TOCTOU"
pass 'Step 3 persist helper refuses symlinked round-start-s'

if grep 'printf.*\*\*⚠ Step 3' "$WRAPPER" | grep -qv '>&2'; then
  fail 'design-step3-review.sh must route Step 3 markdown warnings to stderr'
fi
pass 'Step 3 wrapper keeps stdout KV-only'

D_MISSING=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-missing-result.XXXXXX")
FAKE_MISSING="$D_MISSING/fake-plugin"
make_fake_step3_plugin "$FAKE_MISSING" 'exit 0'
printf 'anchor\n' >"$D_MISSING/plan-review-scope-anchor.txt"
set +e
missing_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_MISSING" DESIGN_TMPDIR="$D_MISSING" ISSUE_NUMBER=9 \
  "$WRAPPER" 2>"$D_MISSING/stderr.log")
missing_rc=$?
set -e
[[ "$missing_rc" -eq 1 ]] || fail "missing result wrapper rc=$missing_rc stdout=$missing_out stderr=$(cat "$D_MISSING/stderr.log")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-init-failed' <<<"$missing_out" || fail 'missing result wrapper should emit STEP3_REVIEW_LOOP_STATUS=panel-init-failed'
grep -Fxq 'LOOP_STATUS=panel-init-failed' <<<"$missing_out" || fail 'missing result wrapper should emit LOOP_STATUS=panel-init-failed'
grep -Fq '**⚠ Step 3: result env missing or empty after loop exit; treating as panel-failed**' "$D_MISSING/stderr.log" || fail 'missing result warning missing from stderr'
grep -Fxq 'SUMMARY_OUTCOME=failed-judge-panel' <<<"$missing_out" || fail 'missing result panel-init summary missing'
rm -rf "$D_MISSING"
pass 'Step 3 wrapper hard-stops missing result env as panel-init-failed'

D_LEGACY=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-legacy-loop.XXXXXX")
FAKE_LEGACY="$D_LEGACY/fake-plugin"
# shellcheck disable=SC2016
make_fake_step3_plugin "$FAKE_LEGACY" 'mkdir -p "$DESIGN_TMPDIR/plan-review/round-1"; printf "reviewer\n" >"$DESIGN_TMPDIR/plan-review/round-1/reviewer-output.txt"; printf "%s\n" "LOOP_STATUS=panel-failed" "ROUNDS_COMPLETED=1" "REVIEW_ROUND_COUNT=1"'
printf 'anchor\n' >"$D_LEGACY/plan-review-scope-anchor.txt"
set +e
legacy_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_LEGACY" DESIGN_TMPDIR="$D_LEGACY" ISSUE_NUMBER=9 \
  "$WRAPPER" 2>"$D_LEGACY/stderr.log")
legacy_rc=$?
set -e
[[ "$legacy_rc" -eq 0 ]] || fail "legacy loop wrapper rc=$legacy_rc stdout=$legacy_out stderr=$(cat "$D_LEGACY/stderr.log")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-failed' <<<"$legacy_out" || fail 'legacy LOOP_STATUS=panel-failed should back-map STEP3_REVIEW_LOOP_STATUS'
grep -Fxq 'LOOP_STATUS=panel-failed' <<<"$legacy_out" || fail 'legacy LOOP_STATUS=panel-failed should survive normalization'
rm -rf "$D_LEGACY"
pass 'Step 3 wrapper back-maps legacy LOOP_STATUS=panel-failed'

D_ZFDP=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-legacy-zfdp.XXXXXX")
FAKE_ZFDP="$D_ZFDP/fake-plugin"
make_fake_step3_plugin "$FAKE_ZFDP" 'printf "%s\n" "LOOP_STATUS=zero-findings-degraded-panel"'
printf 'anchor\n' >"$D_ZFDP/plan-review-scope-anchor.txt"
set +e
zfdp_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_ZFDP" DESIGN_TMPDIR="$D_ZFDP" ISSUE_NUMBER=9 \
  "$WRAPPER" 2>"$D_ZFDP/stderr.log")
zfdp_rc=$?
set -e
[[ "$zfdp_rc" -eq 0 ]] || fail "legacy zero-findings wrapper rc=$zfdp_rc stdout=$zfdp_out stderr=$(cat "$D_ZFDP/stderr.log")"
grep -Fxq 'LOOP_STATUS=zero-findings-degraded-panel' <<<"$zfdp_out" || fail 'legacy LOOP_STATUS=zero-findings-degraded-panel should survive unchanged'
grep -Fq 'STEP3_REVIEW_LOOP_STATUS=' <<<"$zfdp_out" && fail 'legacy zero-findings-degraded-panel must not emit STEP3_REVIEW_LOOP_STATUS'
grep -Fq '**⚠ Step 3: result env missing or empty after loop exit; treating as panel-failed**' "$D_ZFDP/stderr.log" && fail 'zero-findings-degraded-panel must not trigger missing-result warning'
rm -rf "$D_ZFDP"
pass 'Step 3 wrapper preserves legacy LOOP_STATUS=zero-findings-degraded-panel'

D_KILL=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-kill-helper.XXXXXX")
FAKE_KILL="$D_KILL/fake-plugin"
# shellcheck disable=SC2016
make_fake_step3_plugin "$FAKE_KILL" '{
  printf "%s\n" "loop" >> "$ORDER_LOG"
  cat > "$DESIGN_TMPDIR/.step3-review-result.env" <<RESULT
STEP3_REVIEW_LOOP_STATUS=complete
LOOP_STATUS=complete
TALLY_PLAN_REVIEW_STATUS=ok
STEP3_REVIEW_CAP_REACHED=false
ROUNDS_COMPLETED=1
REVIEW_ROUND_COUNT=1
RESULT
}'
printf 'anchor\n' >"$D_KILL/plan-review-scope-anchor.txt"
mkdir -p "$FAKE_KILL/python"
cat >"$FAKE_KILL/python/cli.py" <<'PYEOF'
from __future__ import annotations

import os
import subprocess
import sys

if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] == "run":
    run_sh = os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", ""), "skills", "design", "scripts", "plan-review-loop-stub.sh")
    sys.exit(subprocess.call(["/bin/bash", run_sh]))
# design read-result-env must delegate to the real CLI so result-env reads work
if len(sys.argv) >= 3 and sys.argv[1] == "design" and sys.argv[2] == "read-result-env":
    real_cli = os.path.join(os.environ.get("LARCH_TEST_REAL_REPO_ROOT", ""), "python", "cli.py")
    if real_cli and os.path.isfile(real_cli):
        sys.exit(subprocess.call([sys.executable, real_cli, *sys.argv[1:]]))
    sys.exit(0)
if len(sys.argv) >= 3 and sys.argv[1] == "scope-anchor" and sys.argv[2] == "validate":
    raise SystemExit(0)
if len(sys.argv) >= 3 and sys.argv[1] == "session" and sys.argv[2] == "validate-design-tmpdir":
    raise SystemExit(0)
with open(os.environ["ORDER_LOG"], "a", encoding="utf-8") as handle:
    handle.write("helper " + " ".join(sys.argv[1:]) + "\n")
raise SystemExit(int(os.environ.get("HELPER_RC", "0")))
PYEOF
order_log="$D_KILL/order.log"
set +e
kill_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_KILL" DESIGN_TMPDIR="$D_KILL" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" ORDER_LOG="$order_log" HELPER_RC=73 "$WRAPPER" 2>"$D_KILL/stderr.log")
kill_rc=$?
set -e
[[ "$kill_rc" -eq 0 ]] || fail "kill helper wrapper rc=$kill_rc stdout=$kill_out stderr=$(cat "$D_KILL/stderr.log")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=complete' <<<"$kill_out" || fail 'kill helper failure should preserve complete envelope'
grep -Fxq 'loop' "$order_log" || fail 'loop marker missing before kill helper'
grep -Fq 'helper session kill-background-processes --design-tmpdir' "$order_log" || fail 'kill helper argv missing'
if ! awk 'BEGIN { loop=0; helper=0 } $0=="loop" { loop=NR } /^helper / { helper=NR } END { exit !(loop > 0 && helper > loop) }' "$order_log"; then
  fail 'kill helper must run after loop marker'
fi
rm -rf "$D_KILL"
pass 'Step 3 wrapper invokes tmpdir kill helper after loop and ignores helper failure'

# #4489: the wrapper guarantees the Step 3 completion sentinels on a terminal exit
# even when the (stubbed) inner loop wrote a terminal result env but not the
# sentinel, so hook-bg-poll-guard.sh releases the marker without the dead-process
# race.
D_SENTINEL=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-sentinel.XXXXXX")
FAKE_SENTINEL="$D_SENTINEL/fake-plugin"
# shellcheck disable=SC2016
make_fake_step3_plugin "$FAKE_SENTINEL" 'cat > "$DESIGN_TMPDIR/.step3-review-result.env" <<RESULT
STEP3_REVIEW_LOOP_STATUS=complete
LOOP_STATUS=complete
TALLY_PLAN_REVIEW_STATUS=ok
STEP3_REVIEW_CAP_REACHED=false
ROUNDS_COMPLETED=1
REVIEW_ROUND_COUNT=1
RESULT'
printf 'anchor\n' >"$D_SENTINEL/plan-review-scope-anchor.txt"
[ ! -e "$D_SENTINEL/.completed/step-3" ] || fail 'precondition: step-3 sentinel must be absent before run'
mkdir -p "$D_SENTINEL/.completed"
: >"$D_SENTINEL/.completed/step-3-terminal"
: >"$D_SENTINEL/.step3-terminal-persisted-this-run"
set +e
sentinel_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_SENTINEL" DESIGN_TMPDIR="$D_SENTINEL" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" "$WRAPPER" 2>"$D_SENTINEL/stderr.log")
sentinel_rc=$?
set -e
[[ "$sentinel_rc" -eq 0 ]] || fail "sentinel-guarantee wrapper rc=$sentinel_rc stdout=$sentinel_out stderr=$(cat "$D_SENTINEL/stderr.log")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=complete' <<<"$sentinel_out" || fail 'sentinel-guarantee path should preserve complete envelope'
[ ! -e "$D_SENTINEL/.completed/step-3" ] || fail 'stale result env without current-pass sidecar must not mint step-3'
[ ! -e "$D_SENTINEL/.completed/step-3-terminal" ] || fail 'stale step-3-terminal must be cleared and not recreated from result env alone'
[ ! -e "$D_SENTINEL/.step3-terminal-persisted-this-run" ] || fail 'stale step3 terminal persist sidecar must be cleared at wrapper entry'
[ ! -e "$D_SENTINEL/.completed/step-3.5" ] || fail '#4489: guarantee must not write deferred .completed/step-3.5 (Gate C / pause-resume gate)'
rm -rf "$D_SENTINEL"
pass 'Step 3 wrapper clears stale terminal sentinels and does not mint step-3 from stale result env alone'

D_FRESH_TERMINAL=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-terminal.XXXXXX")
FAKE_FRESH_TERMINAL="$D_FRESH_TERMINAL/fake-plugin"
# shellcheck disable=SC2016 # fake plugin body must preserve runtime $DESIGN_TMPDIR.
make_fake_step3_plugin "$FAKE_FRESH_TERMINAL" 'cat > "$DESIGN_TMPDIR/.step3-review-result.env" <<RESULT
STEP3_REVIEW_LOOP_STATUS=complete
LOOP_STATUS=complete
TALLY_PLAN_REVIEW_STATUS=ok
STEP3_REVIEW_CAP_REACHED=false
ROUNDS_COMPLETED=1
REVIEW_ROUND_COUNT=1
RESULT
: >"$DESIGN_TMPDIR/.step3-terminal-persisted-this-run"'
printf 'anchor\n' >"$D_FRESH_TERMINAL/plan-review-scope-anchor.txt"
set +e
fresh_terminal_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_FRESH_TERMINAL" DESIGN_TMPDIR="$D_FRESH_TERMINAL" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" "$WRAPPER" 2>"$D_FRESH_TERMINAL/stderr.log")
fresh_terminal_rc=$?
set -e
[[ "$fresh_terminal_rc" -eq 0 ]] || fail "fresh-terminal wrapper rc=$fresh_terminal_rc stdout=$fresh_terminal_out stderr=$(cat "$D_FRESH_TERMINAL/stderr.log")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=complete' <<<"$fresh_terminal_out" || fail 'fresh-terminal path should preserve complete envelope'
[ -f "$D_FRESH_TERMINAL/.completed/step-3-terminal" ] || fail 'current-pass persist sidecar must permit terminal sentinel fallback'
[ -f "$D_FRESH_TERMINAL/.step3-terminal-persisted-this-run" ] || fail 'current-pass persist sidecar must remain inspectable'
rm -rf "$D_FRESH_TERMINAL"
pass 'Step 3 wrapper writes step-3-terminal only when current-pass persist sidecar exists'

D_NO_ANCHOR=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-no-anchor.XXXXXX")
FAKE_NO_ANCHOR="$D_NO_ANCHOR/fake-plugin"
make_fake_step3_plugin "$FAKE_NO_ANCHOR" 'printf "%s\n" "SHOULD_NOT_RUN=true"'
set +e
no_anchor_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_NO_ANCHOR" DESIGN_TMPDIR="$D_NO_ANCHOR" ISSUE_NUMBER=9 \
  "$WRAPPER" 2>"$D_NO_ANCHOR/stderr.log")
no_anchor_rc=$?
set -e
[[ "$no_anchor_rc" -eq 1 ]] || fail "no-anchor wrapper rc=$no_anchor_rc stdout=$no_anchor_out stderr=$(cat "$D_NO_ANCHOR/stderr.log")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-init-failed' <<<"$no_anchor_out" || fail 'missing anchor should emit panel-init-failed'
grep -Fxq 'ROUNDS_COMPLETED=0' <<<"$no_anchor_out" || fail 'missing anchor should emit zero rounds'
grep -Fxq 'SUMMARY_OUTCOME=failed-judge-panel' <<<"$no_anchor_out" || fail 'missing anchor summary missing'
if grep -Fq 'SHOULD_NOT_RUN=true' <<<"$no_anchor_out"; then
  fail 'missing anchor must not launch loop'
fi
rm -rf "$D_NO_ANCHOR"
pass 'Step 3 wrapper refuses to launch without scope anchor'

D_ZERO_PANEL=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-zero-panel.XXXXXX")
FAKE_ZERO="$D_ZERO_PANEL/fake-plugin"
make_fake_step3_plugin "$FAKE_ZERO" 'printf "%s\n" "LOOP_STATUS=panel-failed" "ROUNDS_COMPLETED=0" "REVIEW_ROUND_COUNT=0"'
printf 'anchor\n' >"$D_ZERO_PANEL/plan-review-scope-anchor.txt"
set +e
zero_panel_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_ZERO" DESIGN_TMPDIR="$D_ZERO_PANEL" ISSUE_NUMBER=9 \
  "$WRAPPER" 2>"$D_ZERO_PANEL/stderr.log")
zero_panel_rc=$?
set -e
[[ "$zero_panel_rc" -eq 1 ]] || fail "zero-panel wrapper rc=$zero_panel_rc stdout=$zero_panel_out"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-init-failed' <<<"$zero_panel_out" || fail 'zero-round panel-failed should normalize to panel-init-failed'
grep -Fxq 'SUMMARY_OUTCOME=failed-judge-panel' <<<"$zero_panel_out" || fail 'zero-round panel-failed summary missing'
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-init-failed' "$D_ZERO_PANEL/.step3-review-result.env" || fail 'zero-round normalization must persist result env'
grep -Fxq 'ROUNDS_COMPLETED=0' "$D_ZERO_PANEL/.step3-review-result.env" || fail 'zero-round normalization must zero rounds in result env'
rm -rf "$D_ZERO_PANEL"
pass 'Step 3 wrapper normalizes zero-round panel-failed to panel-init-failed'

D_DEGRADED_ZERO=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-degraded-zero.XXXXXX")
FAKE_DEGRADED="$D_DEGRADED_ZERO/fake-plugin"
make_fake_step3_plugin "$FAKE_DEGRADED" 'printf "%s\n" "LOOP_STATUS=panel-failed" "ROUNDS_COMPLETED=0" "REVIEW_ROUND_COUNT=0" "DEGRADED_PANEL=1"'
printf 'anchor\n' >"$D_DEGRADED_ZERO/plan-review-scope-anchor.txt"
set +e
degraded_zero_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_DEGRADED" DESIGN_TMPDIR="$D_DEGRADED_ZERO" ISSUE_NUMBER=9 \
  "$WRAPPER" 2>"$D_DEGRADED_ZERO/stderr.log")
degraded_zero_rc=$?
set -e
[[ "$degraded_zero_rc" -eq 1 ]] || fail "degraded-zero wrapper rc=$degraded_zero_rc stdout=$degraded_zero_out"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-init-failed' <<<"$degraded_zero_out" || fail 'degraded zero-round panel-failed should hard-stop'
rm -rf "$D_DEGRADED_ZERO"
pass 'Step 3 wrapper hard-stops degraded zero-round panel-failed'

D_EMPTY_R1=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-empty-r1.XXXXXX")
FAKE_EMPTY_R1="$D_EMPTY_R1/fake-plugin"
# shellcheck disable=SC2016
make_fake_step3_plugin "$FAKE_EMPTY_R1" 'mkdir -p "$DESIGN_TMPDIR/plan-review/round-1"; printf "%s\n" "LOOP_STATUS=panel-failed" "ROUNDS_COMPLETED=1" "REVIEW_ROUND_COUNT=1" "DEGRADED_PANEL=1"'
printf 'anchor\n' >"$D_EMPTY_R1/plan-review-scope-anchor.txt"
set +e
empty_r1_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_EMPTY_R1" DESIGN_TMPDIR="$D_EMPTY_R1" ISSUE_NUMBER=9 \
  "$WRAPPER" 2>"$D_EMPTY_R1/stderr.log")
empty_r1_rc=$?
set -e
[[ "$empty_r1_rc" -eq 1 ]] || fail "empty-r1 wrapper rc=$empty_r1_rc stdout=$empty_r1_out"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-init-failed' <<<"$empty_r1_out" || fail 'empty round-1 with nonzero rounds should normalize to panel-init-failed'
rm -rf "$D_EMPTY_R1"
pass 'Step 3 wrapper treats empty round-1 as zero reviewer coverage'

# #4431 Fix C: --read-result-env recovers loop status without running the review
# (hook-safe wrapper-routed fallback for when the poll guard blocks a direct read).
RRE_PLUGIN=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-rre-plugin.XXXXXX")
make_fake_step3_plugin "$RRE_PLUGIN" 'exit 0'
D_RRE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-rre.XXXXXX")
cat > "$D_RRE/.step3-review-result.env" <<'RESULT'
STEP3_REVIEW_LOOP_STATUS=tally-error
LOOP_STATUS=tally-error
ROUNDS_COMPLETED=1
FINAL_ROUND_NUM=1
ACCEPTED_COUNT=0
RESULT
set +e
rre_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$RRE_PLUGIN" DESIGN_TMPDIR="$D_RRE" ISSUE_NUMBER=9 \
  "$WRAPPER" --read-result-env)
rre_rc=$?
set -e
[[ "$rre_rc" -eq 0 ]] || fail "--read-result-env rc=$rre_rc out=$rre_out"
grep -Fxq 'READ_RESULT_ENV_STATUS=ok' <<<"$rre_out" || fail '--read-result-env must report ok when result env present'
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=tally-error' <<<"$rre_out" || fail '--read-result-env must emit STEP3_REVIEW_LOOP_STATUS from result env'
grep -Fxq 'ROUNDS_COMPLETED=1' <<<"$rre_out" || fail '--read-result-env must emit ROUNDS_COMPLETED from result env'
[ ! -f "$D_RRE/.bg-wait-active" ] || fail '--read-result-env must not start the bg-wait marker'
[ ! -d "$D_RRE/plan-review" ] || fail '--read-result-env must not dispatch the review'
[ ! -e "$D_RRE/.completed/step-3" ] || fail '--read-result-env must not write the completion sentinel (#4489)'

D_RRE_MISSING=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-rre-missing.XXXXXX")
set +e
rre_missing_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$RRE_PLUGIN" DESIGN_TMPDIR="$D_RRE_MISSING" ISSUE_NUMBER=9 \
  "$WRAPPER" --read-result-env)
rre_missing_rc=$?
set -e
[[ "$rre_missing_rc" -eq 0 ]] || fail "--read-result-env (missing) rc=$rre_missing_rc out=$rre_missing_out"
grep -Fxq 'READ_RESULT_ENV_STATUS=missing' <<<"$rre_missing_out" || fail '--read-result-env must report missing when result env absent'
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=' <<<"$rre_missing_out" || fail '--read-result-env must emit empty STEP3_REVIEW_LOOP_STATUS when result env absent'
rm -rf "$RRE_PLUGIN" "$D_RRE" "$D_RRE_MISSING"
pass 'Step 3 --read-result-env recovers loop status (hook-safe fallback)'

D_PERSIST_TERMINAL=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-persist-terminal.XXXXXX")
# shellcheck disable=SC2016
cat >"$D_PERSIST_TERMINAL/run-persist.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
export DESIGN_TMPDIR="$1"
export PLUGIN_ROOT="$2"
export mode="$3"
emit() { :; }
emit_kv() { :; }
larch_err() { :; }
phase_driver_write_result_env() {
  if [[ "$mode" == fail ]]; then
    return 1
  fi
  printf '%s\n' "$@" >"$1"
  return 0
}
# shellcheck source=/dev/null
source "$PLUGIN_ROOT/skills/design/scripts/review-design-step3-loop.sh"
step3_loop_persist_envelope main-agent-apply-required 1 1 1 "" ""
SH
chmod +x "$D_PERSIST_TERMINAL/run-persist.sh"
"$D_PERSIST_TERMINAL/run-persist.sh" "$D_PERSIST_TERMINAL" "$ROOT" success
[ -f "$D_PERSIST_TERMINAL/.completed/step-3-terminal" ] || fail 'persist success must write step-3-terminal'
[ -f "$D_PERSIST_TERMINAL/.step3-terminal-persisted-this-run" ] || fail 'persist success must write persist sidecar'
rm -rf "$D_PERSIST_TERMINAL/.completed" "$D_PERSIST_TERMINAL/.step3-review-result.env" "$D_PERSIST_TERMINAL/.step3-terminal-persisted-this-run"
set +e
"$D_PERSIST_TERMINAL/run-persist.sh" "$D_PERSIST_TERMINAL" "$ROOT" fail
persist_fail_rc=$?
set -e
[[ "$persist_fail_rc" -ne 0 ]] || fail 'persist failure must return non-zero'
[ ! -e "$D_PERSIST_TERMINAL/.completed/step-3-terminal" ] || fail 'persist failure must not write step-3-terminal'
[ ! -e "$D_PERSIST_TERMINAL/.step3-terminal-persisted-this-run" ] || fail 'persist failure must not write persist sidecar'
rm -rf "$D_PERSIST_TERMINAL"
pass 'Step 3 loop writes terminal sentinel only after persist success'

D_APPLY_REQUIRED=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-apply-required.XXXXXX")
FAKE_APPLY="$D_APPLY_REQUIRED/fake-plugin"
# shellcheck disable=SC2016
make_fake_step3_plugin "$FAKE_APPLY" 'cat > "$DESIGN_TMPDIR/.step3-review-result.env" <<RESULT
STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required
LOOP_STATUS=complete
TALLY_PLAN_REVIEW_STATUS=main-agent-apply-required
STEP3_REVIEW_CAP_REACHED=false
ROUNDS_COMPLETED=1
REVIEW_ROUND_COUNT=1
RESULT
mkdir -p "$DESIGN_TMPDIR/.completed"
: >"$DESIGN_TMPDIR/.completed/step-3-terminal"
: >"$DESIGN_TMPDIR/.step3-terminal-persisted-this-run"'
printf 'anchor\n' >"$D_APPLY_REQUIRED/plan-review-scope-anchor.txt"
set +e
apply_required_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_APPLY" DESIGN_TMPDIR="$D_APPLY_REQUIRED" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" "$WRAPPER" 2>"$D_APPLY_REQUIRED/stderr.log")
apply_required_rc=$?
set -e
[[ "$apply_required_rc" -eq 0 ]] || fail "apply-required wrapper rc=$apply_required_rc stdout=$apply_required_out stderr=$(cat "$D_APPLY_REQUIRED/stderr.log")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required' <<<"$apply_required_out" || fail 'apply-required path should preserve envelope'
[ -f "$D_APPLY_REQUIRED/.completed/step-3-terminal" ] || fail 'apply-required mid-loop bail must retain step-3-terminal'
[ -f "$D_APPLY_REQUIRED/.step3-terminal-persisted-this-run" ] || fail 'apply-required mid-loop bail must retain persist sidecar'
[ ! -e "$D_APPLY_REQUIRED/.completed/step-3" ] || fail 'apply-required mid-loop bail must not mint step-3'
rm -rf "$D_APPLY_REQUIRED"
pass 'Step 3 wrapper does not mint step-3 on main-agent-apply-required bail-out'

D_MAV_VOTE=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-mav-vote.XXXXXX")
FAKE_MAV="$D_MAV_VOTE/fake-plugin"
# shellcheck disable=SC2016
make_fake_step3_plugin "$FAKE_MAV" 'cat > "$DESIGN_TMPDIR/.step3-review-result.env" <<RESULT
STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required
LOOP_STATUS=main-agent-vote-required
TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required
STEP3_REVIEW_CAP_REACHED=false
ROUNDS_COMPLETED=1
REVIEW_ROUND_COUNT=1
RESULT
: >"$DESIGN_TMPDIR/.step3-terminal-persisted-this-run"
mkdir -p "$DESIGN_TMPDIR/.completed"
: >"$DESIGN_TMPDIR/.completed/step-3-terminal"'
printf 'anchor\n' >"$D_MAV_VOTE/plan-review-scope-anchor.txt"
set +e
mav_vote_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_MAV" DESIGN_TMPDIR="$D_MAV_VOTE" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" "$WRAPPER" 2>"$D_MAV_VOTE/stderr.log")
mav_vote_rc=$?
set -e
[[ "$mav_vote_rc" -eq 0 ]] || fail "mav-vote wrapper rc=$mav_vote_rc stdout=$mav_vote_out stderr=$(cat "$D_MAV_VOTE/stderr.log")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required' <<<"$mav_vote_out" || fail 'mav-vote path should preserve envelope'
[ -f "$D_MAV_VOTE/.completed/step-3-terminal" ] || fail 'mav-vote mid-loop bail must retain step-3-terminal'
[ ! -e "$D_MAV_VOTE/.completed/step-3" ] || fail 'mav-vote mid-loop bail must not mint step-3'
rm -rf "$D_MAV_VOTE"
pass 'Step 3 wrapper does not mint step-3 on main-agent-vote-required bail-out'

D_STALE_ENV=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-stale-env.XXXXXX")
FAKE_STALE="$D_STALE_ENV/fake-plugin"
cat >"$D_STALE_ENV/.step3-review-result.env" <<'RESULT'
STEP3_REVIEW_LOOP_STATUS=complete
LOOP_STATUS=complete
TALLY_PLAN_REVIEW_STATUS=ok
ROUNDS_COMPLETED=1
REVIEW_ROUND_COUNT=1
RESULT
mkdir -p "$D_STALE_ENV/.completed"
: >"$D_STALE_ENV/.completed/step-3"
# shellcheck disable=SC2016
make_fake_step3_plugin "$FAKE_STALE" 'if grep -Fq "STEP3_REVIEW_LOOP_STATUS=complete" "$DESIGN_TMPDIR/.step3-review-result.env" 2>/dev/null; then
  : >"$DESIGN_TMPDIR/.stale-env-seen"
fi
exit 1'
printf 'anchor\n' >"$D_STALE_ENV/plan-review-scope-anchor.txt"
set +e
env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_STALE" DESIGN_TMPDIR="$D_STALE_ENV" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" "$WRAPPER" >/dev/null 2>"$D_STALE_ENV/stderr.log"
stale_env_rc=$?
set -e
[[ "$stale_env_rc" -ne 0 ]] || fail "stale-env wrapper should fail before loop (rc=$stale_env_rc)"
[ ! -e "$D_STALE_ENV/.stale-env-seen" ] || fail 'stale complete result env must be cleared before loop dispatch'
rm -rf "$D_STALE_ENV"
pass 'Step 3 wrapper clears stale result env and step-3 at non-resume entry'

D_STALE_STEP3=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-stale-step3.XXXXXX")
FAKE_STALE_STEP3="$D_STALE_STEP3/fake-plugin"
mkdir -p "$D_STALE_STEP3/.completed"
: >"$D_STALE_STEP3/.completed/step-3"
cat >"$D_STALE_STEP3/.step3-round-1.phase" <<'PHASE'
awaiting-continuation
PHASE
make_fake_step3_plugin "$FAKE_STALE_STEP3" 'printf "%s\n" "STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required" "LOOP_STATUS=main-agent-vote-required" "ROUNDS_COMPLETED=1" "REVIEW_ROUND_COUNT=1"'
printf 'anchor\n' >"$D_STALE_STEP3/plan-review-scope-anchor.txt"
set +e
env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_STALE_STEP3" DESIGN_TMPDIR="$D_STALE_STEP3" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" "$WRAPPER" --starting-round 1 --phase awaiting-continuation >/dev/null 2>"$D_STALE_STEP3/stderr.log"
stale_step3_rc=$?
set -e
[[ "$stale_step3_rc" -eq 0 ]] || fail "stale-step3 resume wrapper rc=$stale_step3_rc"
[ ! -e "$D_STALE_STEP3/.completed/step-3" ] || fail 'mid-loop resume must clear stale step-3 milestone'
rm -rf "$D_STALE_STEP3"
pass 'Step 3 wrapper clears stale step-3 on mid-loop resume entry'

D_PERSIST_EMIT=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-persist-emit.XXXXXX")
# shellcheck disable=SC2016
cat >"$D_PERSIST_EMIT/run-emit.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
export DESIGN_TMPDIR="$1"
export PLUGIN_ROOT="$2"
export mode="$3"
emit() { printf '%s\n' "$*"; }
emit_kv() { printf '%s=%s\n' "$1" "$2"; }
larch_err() { :; }
phase_driver_write_result_env() {
  if [[ "$mode" == fail ]]; then
    return 1
  fi
  printf '%s\n' "$@" >"$1"
  return 0
}
# shellcheck source=/dev/null
source "$PLUGIN_ROOT/skills/design/scripts/review-design-step3-loop.sh"
step3_loop_emit_envelope complete 1 1 1
SH
chmod +x "$D_PERSIST_EMIT/run-emit.sh"
mkdir -p "$D_PERSIST_EMIT/.completed"
: >"$D_PERSIST_EMIT/.completed/step-3"
emit_out=$("$D_PERSIST_EMIT/run-emit.sh" "$D_PERSIST_EMIT" "$ROOT" success)
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=complete' <<<"$emit_out" || fail 'persist success must emit terminal status KVs after persist'
[ -f "$D_PERSIST_EMIT/.completed/step-3-terminal" ] || fail 'persist success must write step-3-terminal before stdout emit'
emit_fail_out=$("$D_PERSIST_EMIT/run-emit.sh" "$D_PERSIST_EMIT" "$ROOT" fail 2>/dev/null || true)
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=complete' <<<"$emit_fail_out" && fail 'persist failure must not emit terminal STEP3_REVIEW_LOOP_STATUS'
grep -Fq 'WARN=step3_loop_persist_envelope: phase_driver_write_result_env failed' <<<"$emit_fail_out" || fail 'persist failure must emit WARN KV'
rm -rf "$D_PERSIST_EMIT"
pass 'Step 3 loop emits terminal stdout only after persist success'

D_PRELAUNCH=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-prelaunch-terminal.XXXXXX")
FAKE_PRELAUNCH="$D_PRELAUNCH/fake-plugin"
make_fake_step3_plugin "$FAKE_PRELAUNCH" 'exit 0'
set +e
prelaunch_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_PRELAUNCH" DESIGN_TMPDIR="$D_PRELAUNCH" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" "$WRAPPER" 2>"$D_PRELAUNCH/stderr.log")
prelaunch_rc=$?
set -e
[[ "$prelaunch_rc" -eq 1 ]] || fail "prelaunch wrapper rc=$prelaunch_rc stdout=$prelaunch_out"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-init-failed' <<<"$prelaunch_out" || fail 'prelaunch failure should emit panel-init-failed'
[ -f "$D_PRELAUNCH/.completed/step-3-terminal" ] || fail 'prelaunch failure must write step-3-terminal'
[ -f "$D_PRELAUNCH/.step3-terminal-persisted-this-run" ] || fail 'prelaunch failure must write persist sidecar'
rm -rf "$D_PRELAUNCH"
pass 'Step 3 prelaunch failure writes terminal sentinel after result env persist'

pass 'design-step3-review.sh checks passed'
