#!/usr/bin/env bash
# test-design-step3-review.sh — static Step 3 reporting contract checks.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
LOOP="$ROOT/skills/design/scripts/review-design-step3-loop.sh"
WRAPPER="$ROOT/skills/design/scripts/design-step3-review.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

make_fake_step3_plugin() {
  local dir="$1" run_body="$2"
  mkdir -p "$dir/scripts" "$dir/skills/design/scripts"
  ln -sf "$ROOT/scripts/read-result-env.sh" "$dir/scripts/read-result-env.sh"
  ln -sf "$ROOT/scripts/lib-quiet.sh" "$dir/scripts/lib-quiet.sh"
  ln -sf "$ROOT/skills/design/scripts/lib-phase-driver.sh" "$dir/skills/design/scripts/lib-phase-driver.sh"
  cat >"$dir/skills/design/scripts/run-step3-review.sh" <<EOFSTUB
#!/usr/bin/env bash
set -euo pipefail
$run_body
EOFSTUB
  chmod +x "$dir/skills/design/scripts/run-step3-review.sh"
}

grep -Fq 'step3_stage_postplan_failed' "$LOOP" || fail 'postplan-failed staging helper missing'
grep -Fq -- '--outcome failed-postplan' "$LOOP" || fail 'failed-postplan outcome not staged'
# shellcheck disable=SC2016
grep -Fq 'record-escalation --site "$site" --trigger "$trigger"' "$LOOP" || fail 'record-escalation call missing'
grep -Fq 'main-agent-vote-required|main-agent-apply-required|postplan-operator-required|panel-failed|tally-error|degraded-empty-collector' "$LOOP" || fail 'escalation/degradation status set missing'
for status in panel-failed tally-error degraded-empty-collector; do
  grep -Fq "$status" "$LOOP" || fail "$status missing"
done
if grep -Fq 'failed-judge-panel' "$LOOP"; then
  fail 'Step 3 must not handle Step 2b.5 failed-judge-panel retry exhaustion'
fi
if grep -Fq 'render-final-summary.sh' "$WRAPPER"; then
  fail 'design-step3-review.sh must not render final summary'
fi
if grep -Fq '**⚠ Step 3: postplan failed' "$WRAPPER"; then
  fail 'postplan-failed stdout must remain KV-only'
fi
grep -Fq 'SUMMARY_OUTCOME=failed-postplan' "$WRAPPER" || fail 'postplan-failed summary KV missing'

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

D_LOOP=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-escalation.XXXXXX")
DESIGN_TMPDIR="$D_LOOP"
export DESIGN_TMPDIR PLUGIN_ROOT="$ROOT"
# shellcheck source=skills/design/scripts/review-design-step3-loop.sh
# shellcheck disable=SC1091
source "$LOOP"
step3_record_report_evidence tally-error
[ -s "$DESIGN_TMPDIR/design-failure-escalation-ledger.tsv" ] || fail 'tally-error must record escalation ledger row'
grep -Fq 'trigger=tally-error' "$DESIGN_TMPDIR/design-failure-escalation-ledger.tsv" || fail 'tally-error ledger trigger missing'
grep -Fq 'phase=validation' "$DESIGN_TMPDIR/design-failure-escalation-ledger.tsv" || fail 'tally-error ledger phase missing'
[ ! -f "$DESIGN_TMPDIR/design-failure-terminal-state.env" ] || fail 'panel degradation must not stage terminal state'
rm -rf "$D_LOOP"
pass 'Step 3 tally-error records escalation evidence without terminal state'

assert_escalation_recorded() {
  local status="$1" expected_phase="$2"
  local dir
  dir=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-escalation-${status}.XXXXXX")
  DESIGN_TMPDIR="$dir"
  export DESIGN_TMPDIR PLUGIN_ROOT="$ROOT"
  # shellcheck source=skills/design/scripts/review-design-step3-loop.sh
  # shellcheck disable=SC1091
  source "$LOOP"
  step3_record_report_evidence "$status"
  [ -s "$DESIGN_TMPDIR/design-failure-escalation-ledger.tsv" ] || fail "${status} must record escalation ledger row"
  grep -Fq "trigger=${status}" "$DESIGN_TMPDIR/design-failure-escalation-ledger.tsv" || fail "${status} ledger trigger missing"
  grep -Fq "phase=${expected_phase}" "$DESIGN_TMPDIR/design-failure-escalation-ledger.tsv" || fail "${status} ledger phase=${expected_phase} missing"
  [ ! -f "$DESIGN_TMPDIR/design-failure-terminal-state.env" ] || fail "${status} must not stage terminal state"
  rm -rf "$dir"
}

for status in main-agent-vote-required main-agent-apply-required panel-failed degraded-empty-collector; do
  assert_escalation_recorded "$status" validation
done
assert_escalation_recorded postplan-operator-required postplan
pass 'Step 3 main-agent and degradation statuses record escalation evidence'

D_REMAP=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-remap.XXXXXX")
DESIGN_TMPDIR="$D_REMAP"
export DESIGN_TMPDIR PLUGIN_ROOT="$ROOT"
# shellcheck source=skills/design/scripts/lib-phase-driver.sh
source "$ROOT/skills/design/scripts/lib-phase-driver.sh"
larch_quiet_init
# shellcheck source=skills/design/scripts/review-design-step3-loop.sh
# shellcheck disable=SC1091
source "$LOOP"
step3_loop_persist_envelope main-agent-apply-required 1 1 1
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required' "$DESIGN_TMPDIR/.step3-review-result.env" || fail 'remap guard: STEP3_REVIEW_LOOP_STATUS must stay main-agent-apply-required'
grep -Fxq 'LOOP_STATUS=complete' "$DESIGN_TMPDIR/.step3-review-result.env" || fail 'remap guard: LOOP_STATUS must remap to complete for main-agent-apply-required'
rm -rf "$D_REMAP"
pass 'Step 3 remap-vs-status guard preserves STEP3_REVIEW_LOOP_STATUS distinct from LOOP_STATUS'

if grep 'printf.*\*\*⚠ Step 3' "$WRAPPER" | grep -qv '>&2'; then
  fail 'design-step3-review.sh must route Step 3 markdown warnings to stderr'
fi
pass 'Step 3 wrapper keeps stdout KV-only'

D_MISSING=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-missing-result.XXXXXX")
FAKE_MISSING="$D_MISSING/fake-plugin"
make_fake_step3_plugin "$FAKE_MISSING" 'exit 0'
set +e
missing_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_MISSING" DESIGN_TMPDIR="$D_MISSING" ISSUE_NUMBER=9 \
  "$WRAPPER" 2>"$D_MISSING/stderr.log")
missing_rc=$?
set -e
[[ "$missing_rc" -eq 0 ]] || fail "missing result wrapper rc=$missing_rc stdout=$missing_out stderr=$(cat "$D_MISSING/stderr.log")"
grep -Fxq 'STEP3_REVIEW_LOOP_STATUS=panel-failed' <<<"$missing_out" || fail 'missing result wrapper should emit STEP3_REVIEW_LOOP_STATUS=panel-failed'
grep -Fxq 'LOOP_STATUS=panel-failed' <<<"$missing_out" || fail 'missing result wrapper should emit LOOP_STATUS=panel-failed'
grep -Fq '**⚠ Step 3: result env missing or empty after loop exit; treating as panel-failed**' "$D_MISSING/stderr.log" || fail 'missing result warning missing from stderr'
rm -rf "$D_MISSING"
pass 'Step 3 wrapper degrades missing result env to panel-failed'

D_LEGACY=$(mktemp -d "${TMPDIR:-/tmp}/test-step3-legacy-loop.XXXXXX")
FAKE_LEGACY="$D_LEGACY/fake-plugin"
make_fake_step3_plugin "$FAKE_LEGACY" 'printf "%s\n" "LOOP_STATUS=panel-failed"'
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
mkdir -p "$FAKE_KILL/python"
cat >"$FAKE_KILL/python/cli.py" <<'PYEOF'
from __future__ import annotations

import os
import sys

with open(os.environ["ORDER_LOG"], "a", encoding="utf-8") as handle:
    handle.write("helper " + " ".join(sys.argv[1:]) + "\n")
raise SystemExit(int(os.environ.get("HELPER_RC", "0")))
PYEOF
order_log="$D_KILL/order.log"
set +e
kill_out=$(env -u LARCH_QUIET_LOG_FILE LARCH_QUIET_DISABLE=1 CLAUDE_PLUGIN_ROOT="$FAKE_KILL" DESIGN_TMPDIR="$D_KILL" ISSUE_NUMBER=9 \
  ORDER_LOG="$order_log" HELPER_RC=73 "$WRAPPER" 2>"$D_KILL/stderr.log")
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

pass 'design-step3-review.sh checks passed'
