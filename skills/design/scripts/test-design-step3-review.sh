#!/usr/bin/env bash
# test-design-step3-review.sh — static Step 3 reporting contract checks.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
LOOP="$ROOT/skills/design/scripts/review-design-step3-loop.sh"
WRAPPER="$ROOT/skills/design/scripts/design-step3-review.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

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
