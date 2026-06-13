#!/usr/bin/env bash
# test-design-failure-report.sh — offline harness for design-failure-report.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
STAGE="$ROOT/skills/design/scripts/design-stage-terminal-state.sh"
SUBJECT="$ROOT/skills/design/scripts/design-failure-report.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

D=$(mktemp -d); trap 'rm -rf "$D"' EXIT
LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1 env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D" --outcome failed-clarify >"$D/missing.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=fallback-print-required' "$D/missing.out" || fail 'missing terminal state did not fallback'
[ -s "$D/design-failure-chat-print.md" ] || fail 'fallback chat print missing'
pass 'failed outcome without state falls back'

D2=$(mktemp -d)
env -u CLAUDE_PLUGIN_ROOT "$STAGE" --design-tmpdir "$D2" --outcome failed-clarify --step clarify --phase clarify-loop --site clarify-loop --trigger failed --bail-reason clarify-hard-halt --exit-code 1 --source-script clarify-loop >/dev/null
LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1 env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D2" --outcome failed-clarify >"$D2/report.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=terminal-failure' "$D2/report.out" || fail 'terminal decision missing'
[ -s "$D2/design-failure-terminal-report.env" ] || fail 'terminal sentinel missing'
if [ -s "$D2/design-failure-chat-print.md" ]; then
  grep -Fq '[Bug] /design terminal:' "$D2/design-failure-chat-print.md" || fail 'design terminal title missing'
elif [ -s "$D2/design-failure-issue-input.md" ]; then
  grep -Fq '[Bug] /design terminal:' "$D2/design-failure-issue-input.md" || fail 'design terminal title missing'
else
  fail 'terminal report artifact missing'
fi
LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1 env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D2" --outcome failed-clarify >"$D2/second.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_REASON=terminal-sentinel-present' "$D2/second.out" || fail 'terminal sentinel did not skip duplicate'
pass 'terminal report and duplicate skip'

D2b=$(mktemp -d)
env -u CLAUDE_PLUGIN_ROOT "$STAGE" --design-tmpdir "$D2b" --outcome failed-clarify --step clarify --phase clarify-loop --site clarify-loop --trigger failed --bail-reason clarify-hard-halt --exit-code 1 --source-script clarify-loop >/dev/null
LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1 env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D2b" --outcome failed-publish >"$D2b/mismatch.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=fallback-print-required' "$D2b/mismatch.out" || fail 'outcome mismatch did not fallback'
grep -Fxq 'DESIGN_FAILURE_REPORT_REASON=terminal-state-outcome-mismatch' "$D2b/mismatch.out" || fail 'outcome mismatch reason missing'
pass 'terminal state outcome mismatch fails closed'

D3=$(mktemp -d)
cat >"$D3/design-failure-escalation-ledger.tsv" <<'ROW'
utc=2026-01-01T00:00:00Z	site=step3-review	trigger=main-agent-vote-required	step=step3	phase=validation	dispatcher=design-step3-review	exit_code=unknown	failure_detail_log=
ROW
LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1 env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D3" --outcome approved >"$D3/escalation.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=escalation-success' "$D3/escalation.out" || fail 'escalation-success decision missing'
if [ -s "$D3/design-failure-chat-print.md" ]; then
  grep -Fq '[Bug] /design escalation:' "$D3/design-failure-chat-print.md" || fail 'design escalation title missing'
elif [ -s "$D3/design-failure-issue-input.md" ]; then
  grep -Fq '[Bug] /design escalation:' "$D3/design-failure-issue-input.md" || fail 'design escalation title missing'
else
  fail 'escalation report artifact missing'
fi
pass 'escalation-success from ledger on approved outcome'

D4=$(mktemp -d)
LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1 env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D4" --outcome cancelled-clarify >"$D4/cancel.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=operator-action-skip' "$D4/cancel.out" || fail 'cancel skip decision missing'
[ -s "$D4/design-failure-operator-action-chat.md" ] || fail 'operator action chat missing'
[ -s "$D4/design-failure-operator-action.env" ] || fail 'operator action sentinel missing'
pass 'cancelled outcome writes operator-action audit'

D5=$(mktemp -d)
CONSUMER_ROOT=$(mktemp -d)
env -u CLAUDE_PLUGIN_ROOT "$STAGE" --design-tmpdir "$D5" --outcome failed-clarify --step clarify --phase clarify-loop --site clarify-loop --trigger failed --bail-reason clarify-hard-halt --exit-code 1 --source-script clarify-loop >/dev/null
CLAUDE_PROJECT_DIR="$CONSUMER_ROOT" LARCH_STALL_RECOVERY_DRY_RUN=1 env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D5" --outcome failed-clarify >"$D5/consumer.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=terminal-failure' "$D5/consumer.out" || fail 'consumer tree terminal decision missing'
[ -s "$D5/design-failure-chat-print.md" ] || fail 'consumer tree must use chat-print surface'
[ ! -s "$D5/design-failure-issue-input.md" ] || fail 'consumer tree must not write issue-input surface'
pass 'consumer working tree uses chat-print without legacy surfaces flag'

printf 'PASS: test-design-failure-report.sh\n'
