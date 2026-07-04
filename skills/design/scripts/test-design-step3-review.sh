#!/usr/bin/env bash
# test-design-step3-review.sh — static Step 3 reporting contract checks.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
MODULE="$ROOT/python/larch/review/plan_review.py"
NORMALIZE_MODULE="$ROOT/python/larch/review/plan_review_normalize.py"
WRAPPER="$ROOT/skills/design/scripts/design-step3-review.sh"
SKILL_MD="$ROOT/skills/design/SKILL.md"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

make_fake_step3_plugin() {
  local dir="$1" run_body="$2"
  mkdir -p "$dir/scripts" "$dir/skills/design/scripts" "$dir/python"
  cat >"$dir/skills/design/scripts/plan-review-loop-stub.sh" <<EOFSTUB
#!/usr/bin/env bash
set -euo pipefail
$run_body
EOFSTUB
  chmod +x "$dir/skills/design/scripts/plan-review-loop-stub.sh"
  cat >"$dir/python/cli.py" <<'CLIPY'
#!/usr/bin/env python3
import os
import subprocess
import sys

BAKED_REAL_ROOT = "__LARCH_TEST_REAL_ROOT__"
if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] == "run" and "--record-report-evidence" not in sys.argv[3:]:
    run_sh = os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", ""), "skills", "design", "scripts", "plan-review-loop-stub.sh")
    sys.exit(subprocess.call(["/bin/bash", run_sh]))
real_root = os.environ.get("LARCH_TEST_REAL_REPO_ROOT") or BAKED_REAL_ROOT
real_cli = os.path.join(real_root, "python", "cli.py")
if real_cli and os.path.isfile(real_cli):
    sys.exit(subprocess.call([sys.executable, real_cli, *sys.argv[1:]]))
sys.exit(0)
CLIPY
  python3 - "$dir/python/cli.py" "$ROOT" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
path.write_text(path.read_text(encoding="utf-8").replace("__LARCH_TEST_REAL_ROOT__", sys.argv[2]), encoding="utf-8")
PY
  chmod +x "$dir/python/cli.py"
}

grep -Fq 'step3_stage_postplan_failed' "$NORMALIZE_MODULE" || fail 'postplan-failed staging helper missing'
grep -Fq 'failed-postplan' "$NORMALIZE_MODULE" || fail 'failed-postplan outcome not staged'
# shellcheck disable=SC2016
( command grep -Fq 'record-escalation' "$NORMALIZE_MODULE" ) || fail 'record-escalation call missing'
# shellcheck disable=SC2016
( command grep -Fq -- 'step3-review' "$MODULE" ) || fail 'record-escalation site missing'
grep -Fq 'main-agent-vote-required' "$MODULE" || fail 'escalation/degradation status set missing'
python3 - "$MODULE" <<'PY' || fail 'round-start persist contract missing or misordered'
from __future__ import annotations

import sys
from pathlib import Path

body = Path(sys.argv[1]).read_text(encoding="utf-8")
required = [
    "persist_design_round_start_s",
    "plan-review persist-round-start-s",
    "_run_round_body",
]
missing = [item for item in required if item not in body]
if missing:
    raise SystemExit(f"missing helper substrings: {missing}")
if body.index("persist_design_round_start_s") > body.index("_run_round_body"):
    raise SystemExit("persist must be defined before _run_round_body")
PY
pass 'Step 3 loop persists round-start-s before round body with symlink guards'
for status in panel-failed tally-error degraded-empty-collector; do
  grep -Fq "$status" "$MODULE" || fail "$status missing"
done
grep -Fq '**⚠ /design Step 3: all plan reviewers failed at runtime; main agent is self-reviewing the plan before Gate C.**' "$SKILL_MD" \
  || fail 'Step 3 degraded-empty-collector self-review warning missing from skill'
grep -Fq 'Do not enter Gate B because there is no findings list to vote or apply.' "$SKILL_MD" \
  || fail 'Step 3 degraded-empty-collector must bypass Gate B after self-review'
# shellcheck disable=SC2016
grep -Fq "\`NEXT_ACTION=step3b-bypass\` for all other bypass statuses" "$SKILL_MD" \
  || fail 'Step 3 panel-failed/tally-error ordinary bypass branch missing'
if grep -Fq 'degraded-empty-collector, and MAV re-tally tally-error' "$SKILL_MD"; then
  fail 'Step 3 degraded-empty-collector must not be grouped with ordinary bypass statuses'
fi
# Step 3 stages panel-init-failed under the shared failed-judge-panel summary
# outcome: the orchestrator maps panel-init-failed to SUMMARY_OUTCOME=failed-judge-panel
# and the terminal-failure report requires the staged outcome to match it, so the
# canonical staging in plan_review_normalize.py carries failed-judge-panel (restored
# after the sh-to-py port regressed it to panel-init-failed). What Step 3 must NOT own
# is the Step 2b.5 decompose-panel retry exhaustion, whose Split-path staging is
# uniquely marked by the decompose-panel site/trigger.
if grep -Fq 'decompose-panel' "$MODULE"; then
  fail 'Step 3 must not handle Step 2b.5 decompose-panel retry exhaustion'
fi
if grep -Fq 'render-final-summary.sh' "$WRAPPER"; then
  fail 'design-step3-review.sh must not render final summary'
fi
if grep -Fq '**⚠ Step 3: postplan failed' "$WRAPPER"; then
  fail 'postplan-failed stdout must remain KV-only'
fi
grep -Fq 'plan-review normalize-status' "$WRAPPER" || fail 'normalizer delegation missing'
grep -Fq 'SUMMARY_OUTCOME=failed-postplan' "$NORMALIZE_MODULE" || fail 'postplan-failed summary KV missing from normalizer'
grep -Fq 'SUMMARY_OUTCOME=failed-judge-panel' "$NORMALIZE_MODULE" || fail 'panel-init-failed summary KV missing from normalizer'
grep -Fq 'file=sys.stderr' "$NORMALIZE_MODULE" || fail 'normalizer markdown warnings must route to stderr'
grep -Fq 'load_bash_quoted_env' "$NORMALIZE_MODULE" || fail 'normalizer must load quoted env values'
grep -Fq '_step3_read_result_env_quiet' "$MODULE" || fail 'quiet read-result-env helper missing'
# shellcheck disable=SC2016
if grep -Fq 'kill -- -"$_pid"' "$WRAPPER" || grep -Fq 'kill -- -"$_loop_pid"' "$WRAPPER"; then
  fail 'Step 3 wrapper must not raw-kill retained loop pids'
fi
grep -Fq 'plan-review write-loop-identity' "$WRAPPER" || fail 'Step 3 wrapper must write loop identity sidecar after launch'
grep -Fq 'plan-review teardown-loop-identity' "$WRAPPER" || fail 'Step 3 wrapper must delegate loop teardown to identity helper'
# shellcheck disable=SC2016
grep -Fq 'rm -f "$DESIGN_TMPDIR/.step3-loop-identity.json"' "$WRAPPER" || fail 'Step 3 wrapper must clear loop identity sidecar after wait'
python3 - "$WRAPPER" <<'PY' || fail 'Step 3 detach marker write must be guarded by loop identity publication'
from pathlib import Path
import sys

body = Path(sys.argv[1]).read_text(encoding="utf-8")
guard = body.index('if [ "${_step3_review_loop_identity_ready:-false}" = true ]; then')
marker = body.index('_step3_review_write_detached_marker "$_loop_pid" "$_step3_review_external_signal" "$_plan_review_stdout_file"')
if guard > marker:
    raise SystemExit("detach marker write must be guarded by loop identity publication")
PY
pass 'Step 3 wrapper uses identity-validated loop teardown'

D_STEP3=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-stage.XXXXXX")
trap 'rm -rf "$D_STEP3"' EXIT
CLAUDE_PLUGIN_ROOT="$ROOT" python3 "$ROOT/python/cli.py" design stage-terminal-state --design-tmpdir "$D_STEP3" \
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
export CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT"
export LARCH_QUIET_DISABLE=1
export RUN_STEP3_PLAN_REVIEW_LOOP_SH="$DESIGN_TMPDIR/plan-review-loop-stub.sh"
export RUN_STEP3_CONTINUATION_SH="$DESIGN_TMPDIR/continuation.sh"
cat >"$DESIGN_TMPDIR/plan-review-loop-stub.sh" <<'STUB'
#!/usr/bin/env bash
set -euo pipefail
: >"$DESIGN_TMPDIR/body-entered"
waited=0
while [[ ! -f "$DESIGN_TMPDIR/release-body" && "$waited" -lt 50 ]]; do
  sleep 0.1
  waited=$((waited + 1))
done
printf '%s\n' 'LOOP_STATUS=complete' 'TALLY_PLAN_REVIEW_STATUS=ok' 'ACCEPTED_COUNT=0'
STUB
chmod +x "$DESIGN_TMPDIR/plan-review-loop-stub.sh"
printf '{"schema_version":3}\n' >"$DESIGN_TMPDIR/run-params.json"
printf '# Plan\n\ndiff_lines: 1\n' >"$DESIGN_TMPDIR/plan.txt"
printf 'feature\n' >"$DESIGN_TMPDIR/feature-description.txt"
python3 "$PLUGIN_ROOT/python/cli.py" plan-review run --design-tmpdir "$DESIGN_TMPDIR" --no-preview
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
waited=0
while [[ ! -f "$D_ROUND_START/body-entered" && "$waited" -lt 100 ]]; do
  sleep 0.1
  waited=$((waited + 1))
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
ln -s "$OUTSIDE" "$D_PERSIST_GUARD/plan-review"
python3 "$ROOT/python/cli.py" plan-review persist-round-start-s \
  --design-tmpdir "$D_PERSIST_GUARD" --round-num 1 --start-s 12345
[[ ! -e "$OUTSIDE/round-1/round-start-s" ]] || fail 'persist must not follow symlinked plan-review parent'
rm "$D_PERSIST_GUARD/plan-review"
printf 'x\n' >"$D_PERSIST_GUARD/plan-review"
set +e
python3 "$ROOT/python/cli.py" plan-review persist-round-start-s \
  --design-tmpdir "$D_PERSIST_GUARD" --round-num 1 --start-s 12345
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
# #4724: panel-failed with launched reviewer rounds but no loop-persisted result
# env must still synthesize the result env and mint the completion sentinel so the
# orchestrator's Step 3 foreground recovery probe resolves instead of the
# orchestrator yielding forever.
[ -f "$D_LEGACY/.step3-review-result.env" ] || fail '#4724: panel-failed without a persisted result env must synthesize one'
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-failed' "$D_LEGACY/.step3-review-result.env" || fail '#4724: synthesized result env must carry the terminal failure status'
[ -e "$D_LEGACY/.completed/step-3" ] || fail '#4724: panel-failed with launched rounds but no persisted result env must still mint the step-3 completion sentinel'
rm -rf "$D_LEGACY"
pass 'Step 3 wrapper back-maps legacy LOOP_STATUS=panel-failed'

# #4724: same release guarantee for degraded-empty-collector (the other terminal
# status the original report observed) — launched rounds, no loop-persisted result
# env, so the wrapper must synthesize it and write the completion sentinel.
D_SYNTH=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-synth-result.XXXXXX")
FAKE_SYNTH="$D_SYNTH/fake-plugin"
# shellcheck disable=SC2016
make_fake_step3_plugin "$FAKE_SYNTH" 'mkdir -p "$DESIGN_TMPDIR/plan-review/round-1"; printf "reviewer\n" >"$DESIGN_TMPDIR/plan-review/round-1/reviewer-output.txt"; printf "%s\n" "LOOP_STATUS=degraded-empty-collector" "ROUNDS_COMPLETED=1" "REVIEW_ROUND_COUNT=1"'
printf 'anchor\n' >"$D_SYNTH/plan-review-scope-anchor.txt"
[ ! -e "$D_SYNTH/.step3-review-result.env" ] || fail 'precondition: synth result env must be absent before run'
set +e
synth_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_SYNTH" DESIGN_TMPDIR="$D_SYNTH" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" "$WRAPPER" 2>"$D_SYNTH/stderr.log")
synth_rc=$?
set -e
[[ "$synth_rc" -eq 0 ]] || fail "synth-result wrapper rc=$synth_rc stdout=$synth_out stderr=$(cat "$D_SYNTH/stderr.log")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=degraded-empty-collector' <<<"$synth_out" || fail 'synth path should preserve degraded-empty-collector envelope'
[ -f "$D_SYNTH/.step3-review-result.env" ] || fail '#4724: terminal failure without persisted result env must synthesize one'
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=degraded-empty-collector' "$D_SYNTH/.step3-review-result.env" || fail '#4724: synthesized result env must carry the terminal failure status'
[ -f "$D_SYNTH/.step3-terminal-persisted-this-run" ] || fail '#4724: synthesis must write the terminal persist marker'
[ -e "$D_SYNTH/.completed/step-3" ] || fail '#4724: guarantee trap must mint step-3 after result env synthesis so the orchestrator is released'
rm -rf "$D_SYNTH"
pass 'Step 3 wrapper synthesizes result env + completion sentinel on terminal failure without persisted env (#4724)'

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
# Normalization and every non-loop plan-review verb must delegate to the real CLI.
if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] != "run":
    real_root = os.environ.get("LARCH_TEST_REAL_REPO_ROOT") or "__LARCH_TEST_REAL_ROOT__"
    real_cli = os.path.join(real_root, "python", "cli.py")
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
python3 - "$FAKE_KILL/python/cli.py" "$ROOT" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
path.write_text(path.read_text(encoding="utf-8").replace("__LARCH_TEST_REAL_ROOT__", sys.argv[2]), encoding="utf-8")
PY
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

D_DETACH=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-detach.XXXXXX")
FAKE_DETACH="$D_DETACH/fake-plugin"
mkdir -p "$FAKE_DETACH/skills/design/scripts" "$FAKE_DETACH/python"
cat >"$FAKE_DETACH/skills/design/scripts/plan-review-loop-stub.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' start >>"$DESIGN_TMPDIR/round-starts.log"
: >"$DESIGN_TMPDIR/body-entered"
waited=0
while [[ ! -f "$DESIGN_TMPDIR/release-body" && "$waited" -lt 100 ]]; do
  sleep 0.1
  waited=$((waited + 1))
done
printf '%s\n' 'LOOP_STATUS=complete' 'TALLY_PLAN_REVIEW_STATUS=ok' 'ACCEPTED_COUNT=0'
SH
chmod +x "$FAKE_DETACH/skills/design/scripts/plan-review-loop-stub.sh"
cat >"$D_DETACH/continuation.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'PLAN_REVIEW_CONTINUE=false' 'ACCEPTED_COUNT=0' 'DEGRADED_PANEL=0'
SH
chmod +x "$D_DETACH/continuation.sh"
cat >"$FAKE_DETACH/python/cli.py" <<'PYEOF'
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] == "run":
    if "--new-process-group" in sys.argv[3:]:
        os.setsid()
    run_sh = os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", ""), "skills", "design", "scripts", "plan-review-loop-stub.sh")
    proc = subprocess.run(["/bin/bash", run_sh], text=True, capture_output=True, check=False)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if "LOOP_STATUS=complete" in proc.stdout:
        tmpdir = Path(os.environ["DESIGN_TMPDIR"])
        (tmpdir / ".step3-review-result.env").write_text(
            "\n".join(
                [
                    "STEP3_REVIEW_LOOP_STATUS=complete",
                    "LOOP_STATUS=complete",
                    "TALLY_PLAN_REVIEW_STATUS=ok",
                    "STEP3_REVIEW_CAP_REACHED=false",
                    "ROUNDS_COMPLETED=1",
                    "REVIEW_ROUND_COUNT=1",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        completed = tmpdir / ".completed"
        completed.mkdir(exist_ok=True)
        (completed / "step-3").touch()
        (completed / "step-3-terminal").touch()
        (tmpdir / ".step3-terminal-persisted-this-run").touch()
    raise SystemExit(proc.returncode)
if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] == "write-loop-identity":
    tmpdir = Path(sys.argv[sys.argv.index("--design-tmpdir") + 1])
    pid = int(sys.argv[sys.argv.index("--pid") + 1])
    (tmpdir / ".step3-loop-identity.json").write_text(
        json.dumps({"pid": pid, "pgid": pid, "start_time": "stub", "command_signature": "plan-review run", "expected_signature": "plan-review run"}),
        encoding="utf-8",
    )
    raise SystemExit(0)
if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] == "await-loop-identity":
    tmpdir = Path(sys.argv[sys.argv.index("--design-tmpdir") + 1])
    for _ in range(100):
        result_env = tmpdir / ".step3-review-result.env"
        if result_env.is_file() and not result_env.is_symlink() and "STEP3_REVIEW_LOOP_STATUS=" in result_env.read_text(encoding="utf-8"):
            raise SystemExit(0)
        time.sleep(0.1)
    raise SystemExit(1)
if len(sys.argv) >= 3 and sys.argv[1] == "plan-review" and sys.argv[2] != "run":
    real_root = os.environ.get("LARCH_TEST_REAL_REPO_ROOT") or "__LARCH_TEST_REAL_ROOT__"
    real_cli = os.path.join(real_root, "python", "cli.py")
    sys.exit(subprocess.call([sys.executable, real_cli, *sys.argv[1:]]))
if len(sys.argv) >= 3 and sys.argv[1] == "scope-anchor" and sys.argv[2] == "validate":
    raise SystemExit(0)
if len(sys.argv) >= 3 and sys.argv[1] == "session" and sys.argv[2] == "validate-design-tmpdir":
    raise SystemExit(0)
if len(sys.argv) >= 3 and sys.argv[1] == "session" and sys.argv[2] == "kill-background-processes":
    with open(os.environ["DESIGN_TMPDIR"] + "/unexpected-kill-helper", "a", encoding="utf-8") as handle:
        handle.write("kill\n")
    raise SystemExit(0)
raise SystemExit(0)
PYEOF
python3 - "$FAKE_DETACH/python/cli.py" "$ROOT" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
path.write_text(path.read_text(encoding="utf-8").replace("__LARCH_TEST_REAL_ROOT__", sys.argv[2]), encoding="utf-8")
path.chmod(0o755)
PY
printf '{"schema_version":3}\n' >"$D_DETACH/run-params.json"
printf '# Plan\n\ndiff_lines: 1\n' >"$D_DETACH/plan.txt"
printf 'feature\n' >"$D_DETACH/feature-description.txt"
printf 'anchor\n' >"$D_DETACH/plan-review-scope-anchor.txt"
env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_DETACH" DESIGN_TMPDIR="$D_DETACH" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" RUN_STEP3_CONTINUATION_SH="$D_DETACH/continuation.sh" \
  "$WRAPPER" >"$D_DETACH/first.out" 2>"$D_DETACH/first.err" &
detach_wrapper_pid=$!
cleanup_detach_harness() {
  touch "$D_DETACH/release-body" 2>/dev/null || true
  if kill -0 "$detach_wrapper_pid" 2>/dev/null; then
    kill "$detach_wrapper_pid" 2>/dev/null || true
  fi
  wait "$detach_wrapper_pid" 2>/dev/null || true
  rm -rf "$D_DETACH" 2>/dev/null || true
}
trap cleanup_detach_harness EXIT
waited=0
while [[ ! -f "$D_DETACH/body-entered" && "$waited" -lt 100 ]]; do
  sleep 0.1
  waited=$((waited + 1))
done
[[ -f "$D_DETACH/body-entered" ]] || fail "detach loop body did not start; stderr=$(cat "$D_DETACH/first.err")"
waited=0
while [[ ! -f "$D_DETACH/.step3-loop-identity.json" && "$waited" -lt 100 ]]; do
  sleep 0.1
  waited=$((waited + 1))
done
[[ -f "$D_DETACH/.step3-loop-identity.json" ]] || fail 'detach path must write loop identity before signal'
kill -TERM "$detach_wrapper_pid" 2>/dev/null || true
wait "$detach_wrapper_pid" 2>/dev/null || true
[[ -f "$D_DETACH/.step3-wrapper-detached" ]] || fail 'external TERM must write detached wrapper marker'
if [[ -f "$D_DETACH/design-step3-kill.log.jsonl" ]]; then
  fail 'external TERM must not run identity teardown kill log'
fi
[[ ! -f "$D_DETACH/unexpected-kill-helper" ]] || fail 'external TERM must not run tmpdir kill helper'
touch "$D_DETACH/release-body"
set +e
detach_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_DETACH" DESIGN_TMPDIR="$D_DETACH" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" RUN_STEP3_CONTINUATION_SH="$D_DETACH/continuation.sh" \
  "$WRAPPER" 2>"$D_DETACH/reattach.err")
detach_rc=$?
set -e
[[ "$detach_rc" -eq 0 ]] || fail "reattach wrapper rc=$detach_rc stdout=$detach_out stderr=$(cat "$D_DETACH/reattach.err")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=complete' <<<"$detach_out" || fail 'reattach path must normalize the detached loop result'
[[ "$(wc -l <"$D_DETACH/round-starts.log" | tr -d '[:space:]')" = "1" ]] || fail 'reattach path must not dispatch a second review round'
[[ -f "$D_DETACH/.completed/step-3" ]] || fail 'reattach path must preserve detached loop completion sentinel'
[[ ! -f "$D_DETACH/.step3-wrapper-detached" ]] || fail 'reattach path must clear detached marker after normalization'
[[ -f "$D_DETACH/unexpected-kill-helper" ]] || fail 'reattach path must run tmpdir kill helper before normalization'
trap - EXIT
rm -rf "$D_DETACH"
pass 'Step 3 wrapper detaches live loop on external signal and reattaches without re-dispatch'

# #4489 / #5418: the wrapper clears stale terminal sentinels at entry; normalize-status
# writes step-3-terminal before emitting KV when the resolved status is terminal
# (complete/cap-hit/etc.), so hook-bg-poll-guard.sh releases the marker without
# the dead-process race and the premature-notification probe returns success.
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
[ ! -e "$D_SENTINEL/.completed/step-3" ] || fail '#5418: normalize must not mint step-3 (deferred Gate B milestone)'
[ -e "$D_SENTINEL/.completed/step-3-terminal" ] || fail '#5418: normalize must mint step-3-terminal before emit when status is complete'
[ ! -e "$D_SENTINEL/.step3-terminal-persisted-this-run" ] || fail '#5418: normalize writes only step-3-terminal; sidecar must stay absent so EXIT trap cannot mint step-3'
[ ! -e "$D_SENTINEL/.completed/step-3.5" ] || fail '#4489: guarantee must not write deferred .completed/step-3.5 (Gate C / pause-resume gate)'
rm -rf "$D_SENTINEL"
pass 'Step 3 wrapper clears stale terminal sentinels; normalize mints step-3-terminal before emit without triggering step-3'

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
DEGRADED_PANEL_WARNING=panel degraded
INVALID_SLOT_PANEL_WARNING=invalid slot dropped
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
grep -Fxq 'DEGRADED_PANEL_WARNING=panel degraded' <<<"$rre_out" || fail '--read-result-env must emit DEGRADED_PANEL_WARNING from result env'
grep -Fxq 'INVALID_SLOT_PANEL_WARNING=invalid slot dropped' <<<"$rre_out" || fail '--read-result-env must emit INVALID_SLOT_PANEL_WARNING from result env'
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

D_RRE_SYMLINK=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-rre-symlink.XXXXXX")
printf '%s\n' 'STEP3_REVIEW_LOOP_STATUS=complete' >"$D_RRE_SYMLINK/target.env"
ln -s "$D_RRE_SYMLINK/target.env" "$D_RRE_SYMLINK/.step3-review-result.env"
set +e
rre_symlink_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$RRE_PLUGIN" DESIGN_TMPDIR="$D_RRE_SYMLINK" ISSUE_NUMBER=9 \
  "$WRAPPER" --read-result-env)
rre_symlink_rc=$?
set -e
[[ "$rre_symlink_rc" -eq 0 ]] || fail "--read-result-env (symlink) rc=$rre_symlink_rc out=$rre_symlink_out"
grep -Fxq 'READ_RESULT_ENV_STATUS=missing' <<<"$rre_symlink_out" || fail '--read-result-env must report missing when result env is symlinked'
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=' <<<"$rre_symlink_out" || fail '--read-result-env symlink must emit empty STEP3_REVIEW_LOOP_STATUS'
! grep -Fq 'WARN=' <<<"$rre_symlink_out" || fail '--read-result-env symlink must not emit machine WARN'
rm -rf "$RRE_PLUGIN" "$D_RRE" "$D_RRE_MISSING" "$D_RRE_SYMLINK"
pass 'Step 3 --read-result-env recovers loop status (hook-safe fallback)'

# Invalid-slot degradation uses INVALID_SLOT_PANEL_WARNING in production; the wrapper
# must replay it on the normal completion path, not only via --read-result-env.
D_INVALID_SLOT=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-invalid-slot.XXXXXX")
FAKE_INVALID_SLOT="$D_INVALID_SLOT/fake-plugin"
# shellcheck disable=SC2016
make_fake_step3_plugin "$FAKE_INVALID_SLOT" 'cat > "$DESIGN_TMPDIR/.step3-review-result.env" <<RESULT
STEP3_REVIEW_LOOP_STATUS=complete
LOOP_STATUS=complete
TALLY_PLAN_REVIEW_STATUS=ok
STEP3_REVIEW_CAP_REACHED=false
ROUNDS_COMPLETED=1
REVIEW_ROUND_COUNT=1
INVALID_SLOT_PANEL_WARNING=invalid slot dropped
RESULT'
printf 'anchor\n' >"$D_INVALID_SLOT/plan-review-scope-anchor.txt"
mkdir -p "$D_INVALID_SLOT/.completed"
: >"$D_INVALID_SLOT/.completed/step-3-terminal"
: >"$D_INVALID_SLOT/.step3-terminal-persisted-this-run"
set +e
invalid_slot_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_INVALID_SLOT" DESIGN_TMPDIR="$D_INVALID_SLOT" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" "$WRAPPER" 2>"$D_INVALID_SLOT/stderr.log")
invalid_slot_rc=$?
set -e
[[ "$invalid_slot_rc" -eq 0 ]] || fail "invalid-slot wrapper rc=$invalid_slot_rc stdout=$invalid_slot_out stderr=$(cat "$D_INVALID_SLOT/stderr.log")"
grep -Fxq 'INVALID_SLOT_PANEL_WARNING=invalid slot dropped' <<<"$invalid_slot_out" || fail 'wrapper stdout must replay INVALID_SLOT_PANEL_WARNING from result env'
rm -rf "$D_INVALID_SLOT"
pass 'Step 3 wrapper replays INVALID_SLOT_PANEL_WARNING on completion path'

# #5635: monitor mode replaced by Python process-group isolation via --new-process-group.
# Static guards: the wrapper must not contain monitor-mode artifacts; it must pass
# --new-process-group to plan-review run; it must still redirect worker stderr to the
# dedicated plan-review-loop-stderr.log so no job-control output source remains.
if ( command grep -Fq 'set -m' "$WRAPPER" ); then
  fail '#5635: wrapper must not use set -m (monitor mode removed)'
fi
if ( command grep -Fq 'monitor-mode-unavailable' "$WRAPPER" ); then
  fail '#5635: monitor-mode-unavailable prelaunch path must be removed'
fi
if ( command grep -Fq 'bash-job-control.log' "$WRAPPER" ); then
  fail '#5635: bash-job-control.log redirect must be removed'
fi
# shellcheck disable=SC2016
grep -Fq -- '--new-process-group' "$WRAPPER" || fail '#5635: wrapper must pass --new-process-group to plan-review run'
# shellcheck disable=SC2016
grep -Fq '2>"${DESIGN_TMPDIR}/plan-review-loop-stderr.log"' "$WRAPPER" || fail '#5635: plan-review loop launch must redirect stderr to a dedicated log'
# Runtime guard: a loop that writes to stderr must not leak onto the
# wrapper's stdout/stderr (the task output stream); it must land in the dedicated log.
D_REDIRECT=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-redirect.XXXXXX")
FAKE_REDIRECT="$D_REDIRECT/fake-plugin"
# shellcheck disable=SC2016
make_fake_step3_plugin "$FAKE_REDIRECT" 'printf "%s\n" "STEP3_LOOP_STDERR_SENTINEL_5511" >&2
cat > "$DESIGN_TMPDIR/.step3-review-result.env" <<RESULT
STEP3_REVIEW_LOOP_STATUS=complete
LOOP_STATUS=complete
TALLY_PLAN_REVIEW_STATUS=ok
STEP3_REVIEW_CAP_REACHED=false
ROUNDS_COMPLETED=1
REVIEW_ROUND_COUNT=1
RESULT'
printf 'anchor\n' >"$D_REDIRECT/plan-review-scope-anchor.txt"
mkdir -p "$D_REDIRECT/.completed"
: >"$D_REDIRECT/.completed/step-3-terminal"
: >"$D_REDIRECT/.step3-terminal-persisted-this-run"
set +e
redirect_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_REDIRECT" DESIGN_TMPDIR="$D_REDIRECT" ISSUE_NUMBER=9 \
  LARCH_TEST_REAL_REPO_ROOT="$ROOT" "$WRAPPER" 2>"$D_REDIRECT/stderr.log")
redirect_rc=$?
set -e
[[ "$redirect_rc" -eq 0 ]] || fail "redirect wrapper rc=$redirect_rc stdout=$redirect_out stderr=$(cat "$D_REDIRECT/stderr.log")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=complete' <<<"$redirect_out" || fail '#5511: redirect path should preserve complete envelope'
if grep -Fq 'STEP3_LOOP_STDERR_SENTINEL_5511' <<<"$redirect_out"; then
  fail '#5511: plan-review loop stderr must not reach wrapper stdout (task output stream)'
fi
if grep -Fq 'STEP3_LOOP_STDERR_SENTINEL_5511' "$D_REDIRECT/stderr.log"; then
  fail '#5511: plan-review loop stderr must not reach wrapper stderr (task output stream)'
fi
[ -f "$D_REDIRECT/plan-review-loop-stderr.log" ] || fail '#5511: dedicated plan-review-loop-stderr.log must be created'
grep -Fq 'STEP3_LOOP_STDERR_SENTINEL_5511' "$D_REDIRECT/plan-review-loop-stderr.log" || fail '#5511: loop stderr must be captured in plan-review-loop-stderr.log'
rm -rf "$D_REDIRECT"
pass 'Step 3 wrapper redirects plan-review loop stderr off the task output stream (#5511)'

pass 'design-step3-review.sh checks passed'
