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

pass 'design-step3-review.sh checks passed'
