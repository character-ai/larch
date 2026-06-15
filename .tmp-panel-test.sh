#!/usr/bin/env bash
set -xuo pipefail
export CLAUDE_PLUGIN_ROOT=/Users/zhupanov/larch7
D=$(mktemp -d)
STAGE=/Users/zhupanov/larch7/skills/design/scripts/design-stage-terminal-state.sh
SUBJECT=/Users/zhupanov/larch7/skills/design/scripts/design-failure-report.sh
"$STAGE" --design-tmpdir "$D" --outcome failed-judge-panel --step judge-panel --phase judge-panel --site step3-review --trigger panel-init-failed --bail-reason panel-init-failed --exit-code 1 --source-script design-step3-review --summary-outcome failed-judge-panel >/dev/null
LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1 LARCH_STALL_RECOVERY_DRY_RUN=1 "$SUBJECT" --design-tmpdir "$D" --outcome failed-judge-panel >"$D/out" 2>"$D/err"
cat "$D/out"
grep DESIGN_FAILURE_REPORT_DECISION "$D/out"
