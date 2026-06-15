#!/usr/bin/env bash
# test-design-failure-report.sh — offline harness for design-failure-report.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
STAGE="$ROOT/skills/design/scripts/design-stage-terminal-state.sh"
SUBJECT="$ROOT/skills/design/scripts/design-failure-report.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

stage_terminal() {
  local d=$1 outcome=$2 step=$3 phase=$4 site=$5 trigger=$6 bail=$7 source=$8
  shift 8
  env -u CLAUDE_PLUGIN_ROOT "$STAGE" --design-tmpdir "$d" --outcome "$outcome" \
    --step "$step" --phase "$phase" --site "$site" --trigger "$trigger" \
    --bail-reason "$bail" --exit-code 1 --source-script "$source" \
    --summary-outcome "$outcome" "$@" >/dev/null
}

run_report() {
  local d=$1 outcome=$2 out=$3
  shift 3
  LARCH_STALL_RECOVERY_TEST_LEGACY_SURFACES=1 env -u CLAUDE_PLUGIN_ROOT "$@" \
    "$SUBJECT" --design-tmpdir "$d" --outcome "$outcome" >"$out"
}

D=$(mktemp -d); trap 'rm -rf "$D"' EXIT
run_report "$D" failed-clarify "$D/missing.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=fallback-print-required' "$D/missing.out" || fail 'missing terminal state did not fallback'
[ -s "$D/design-failure-chat-print.md" ] || fail 'fallback chat print missing'
pass 'failed outcome without state falls back'

D2=$(mktemp -d)
stage_terminal "$D2" failed-clarify clarify clarify-loop clarify-loop failed clarify-hard-halt clarify-loop
run_report "$D2" failed-clarify "$D2/report.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=terminal-failure' "$D2/report.out" || fail 'terminal decision missing'
[ -s "$D2/design-failure-terminal-report.env" ] || fail 'terminal sentinel missing'
if [ -s "$D2/design-failure-chat-print.md" ]; then
  grep -Fq '[Bug] /design terminal:' "$D2/design-failure-chat-print.md" || fail 'design terminal title missing'
elif [ -s "$D2/design-failure-issue-input.md" ]; then
  grep -Fq '[Bug] /design terminal:' "$D2/design-failure-issue-input.md" || fail 'design terminal title missing'
else
  fail 'terminal report artifact missing'
fi
run_report "$D2" failed-clarify "$D2/second.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_REASON=terminal-sentinel-present' "$D2/second.out" || fail 'terminal sentinel did not skip duplicate'
pass 'terminal report and duplicate skip'

D2b=$(mktemp -d)
stage_terminal "$D2b" failed-clarify clarify clarify-loop clarify-loop failed clarify-hard-halt clarify-loop
run_report "$D2b" failed-publish "$D2b/mismatch.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=fallback-print-required' "$D2b/mismatch.out" || fail 'outcome mismatch did not fallback'
grep -Fxq 'DESIGN_FAILURE_REPORT_REASON=terminal-state-outcome-mismatch' "$D2b/mismatch.out" || fail 'outcome mismatch reason missing'
pass 'terminal state outcome mismatch fails closed'

D3=$(mktemp -d)
cat >"$D3/design-failure-escalation-ledger.tsv" <<'ROW'
utc=2026-01-01T00:00:00Z	site=step3-review	trigger=main-agent-vote-required	step=step3	phase=validation	dispatcher=design-step3-review	exit_code=unknown	failure_detail_log=
ROW
run_report "$D3" approved "$D3/escalation.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=escalation-success' "$D3/escalation.out" || fail 'escalation-success decision missing'
if [ -s "$D3/design-failure-chat-print.md" ]; then
  grep -Fq '[Bug] /design escalation:' "$D3/design-failure-chat-print.md" || fail 'design escalation title missing'
elif [ -s "$D3/design-failure-issue-input.md" ]; then
  grep -Fq '[Bug] /design escalation:' "$D3/design-failure-issue-input.md" || fail 'design escalation title missing'
else
  fail 'escalation report artifact missing'
fi
pass 'escalation-success from ledger on approved outcome'

D3b=$(mktemp -d)
run_report "$D3b" approved "$D3b/no-ledger.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_REASON=no-escalation-evidence' "$D3b/no-ledger.out" || fail 'approved without ledger did not skip'
pass 'approved without escalation evidence skips'

D4=$(mktemp -d)
run_report "$D4" cancelled-clarify "$D4/cancel.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=operator-action-skip' "$D4/cancel.out" || fail 'cancel skip decision missing'
[ -s "$D4/design-failure-operator-action-chat.md" ] || fail 'operator action chat missing'
[ -s "$D4/design-failure-operator-action.env" ] || fail 'operator action sentinel missing'
pass 'cancelled outcome writes operator-action audit'

D5=$(mktemp -d)
CONSUMER_ROOT=$(mktemp -d)
stage_terminal "$D5" failed-clarify clarify clarify-loop clarify-loop failed clarify-hard-halt clarify-loop
CLAUDE_PROJECT_DIR="$CONSUMER_ROOT" LARCH_STALL_RECOVERY_DRY_RUN=1 env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D5" --outcome failed-clarify >"$D5/consumer.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=terminal-failure' "$D5/consumer.out" || fail 'consumer tree terminal decision missing'
[ -s "$D5/design-failure-chat-print.md" ] || fail 'consumer tree must use chat-print surface'
[ ! -s "$D5/design-failure-issue-input.md" ] || fail 'consumer tree must not write issue-input surface'
pass 'consumer working tree uses chat-print without legacy surfaces flag'

D6=$(mktemp -d)
stage_terminal "$D6" failed-publish publish publish design-publish failed publish-failed design-publish
cat >"$D6/design-failure-escalation-ledger.tsv" <<'ROW'
utc=2026-01-01T00:00:00Z	site=step3-review	trigger=main-agent-vote-required	step=step3	phase=validation	dispatcher=design-step3-review	exit_code=unknown	failure_detail_log=
ROW
run_report "$D6" failed-publish "$D6/terminal-wins.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=terminal-failure' "$D6/terminal-wins.out" || fail 'terminal failure did not win over escalation evidence'
pass 'terminal failure wins over escalation evidence'

D6b=$(mktemp -d)
D6B_RUN_ID=design-session-run-123
stage_terminal "$D6b" failed-publish publish publish design-publish failed publish-failed design-publish --root-cause-hint environment
cat >"$D6b/source-env.sh" <<EOF2
export SESSION_ID='$D6B_RUN_ID'
EOF2
run_report "$D6b" failed-publish "$D6b/environment.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=terminal-failure' "$D6b/environment.out" || fail 'environment terminal decision missing'
grep -Fxq 'verdict=environment' "$D6b/design-failure-root-cause.md" || fail 'environment verdict missing from root-cause artifact'
D6B_ARTIFACT=""
for candidate in "$D6b/design-failure-issue-input.md" "$D6b/design-failure-chat-print.md"; do
  [ -s "$candidate" ] || continue
  D6B_ARTIFACT="$candidate"
  break
done
[ -n "$D6B_ARTIFACT" ] || fail 'environment report artifact missing'
grep -Fq 'verdict=environment' "$D6B_ARTIFACT" || fail 'environment verdict missing from public report'
grep -Fq 'Run ID' "$D6B_ARTIFACT" || fail 'environment report missing Run ID label'
grep -Fq "$D6B_RUN_ID" "$D6B_ARTIFACT" || fail 'source-env SESSION_ID missing from Run ID metadata'
pass 'environment root-cause hint and source-env run id reach report'

D7=$(mktemp -d)
stage_terminal "$D7" failed-clarify clarify clarify-loop clarify-loop failed clarify-hard-halt clarify-loop
printf 'INVALID=not-a-token\n' >>"$D7/design-failure-terminal-state.env"
run_report "$D7" failed-clarify "$D7/invalid.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=fallback-print-required' "$D7/invalid.out" || fail 'invalid terminal state did not fallback'
grep -Fxq 'DESIGN_FAILURE_REPORT_REASON=invalid-terminal-state' "$D7/invalid.out" || fail 'invalid terminal state reason missing'
pass 'invalid terminal state fails closed'

D8=$(mktemp -d)
stage_terminal "$D8" failed-publish publish publish design-publish failed publish-failed design-publish
cat >"$D8/design-failure-operator-action.env" <<'EOF2'
DESIGN_FAILURE_OPERATOR_ACTION=true
REASON=validator-operator-cancel
OUTCOME=operator-action
EOF2
run_report "$D8" failed-publish "$D8/operator-sentinel.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=terminal-failure' "$D8/operator-sentinel.out" || fail 'operator sentinel must not suppress terminal failure'
pass 'stale operator-action sentinel does not suppress terminal failure'

grep -Fq 'panel_failure_evidence_present' "$SUBJECT" || fail 'panel failure evidence helper missing'
grep -Fq 'write_fallback_chat "compose-status-missing"' "$SUBJECT" || fail 'compose-status-missing fallback helper missing'
pass 'panel failure evidence bypass does not emit terminal-failure without compose status'

D9=$(mktemp -d)
cat >"$D9/design-failure-operator-action.env" <<'EOF2'
DESIGN_FAILURE_OPERATOR_ACTION=true
REASON=validator-operator-cancel
OUTCOME=operator-action
EOF2
cat >"$D9/design-failure-escalation-ledger.tsv" <<'ROW'
utc=2026-01-01T00:00:00Z	site=step3-review	trigger=main-agent-vote-required	step=step3	phase=validation	dispatcher=design-step3-review	exit_code=unknown	failure_detail_log=
ROW
run_report "$D9" approved "$D9/operator-escalation.out"
grep -Fxq 'DESIGN_FAILURE_REPORT_REASON=operator-action' "$D9/operator-escalation.out" || fail 'operator sentinel must block escalation-success'
pass 'operator-action sentinel blocks escalation-success only'

for case_spec in \
  'failed-plan-write:publish:plan-write:design-publish:failed:plan-write-failed:design-publish' \
  'failed-publish:publish:publish:design-publish:failed:publish-failed:design-publish' \
  'failed-postplan:postplan:postplan:step3-review:postplan-failed:postplan-failed:design-step3-review' \
  'failed-judge-panel:judge-panel:judge-panel:decompose-panel:decompose-panel-retry-exhausted:decompose-panel-retry-exhausted:split-path' \
  'failed-publish-tail:publish:publish:design-publish:publish-tail-failed:publish-tail-failed:design-step5c'; do
  IFS=: read -r outcome step phase site trigger bail source <<<"$case_spec"
  d=$(mktemp -d)
  stage_terminal "$d" "$outcome" "$step" "$phase" "$site" "$trigger" "$bail" "$source"
  run_report "$d" "$outcome" "$d/outcome.out"
  grep -Fxq 'DESIGN_FAILURE_REPORT_DECISION=terminal-failure' "$d/outcome.out" || fail "terminal gate missing for $outcome"
  pass "terminal gate accepts $outcome"
done

assert_sensitive_leak_blocked() {
  local label=$1 leak_file=$2 marker=$3
  local d consumer report
  d=$(mktemp -d)
  consumer=$(mktemp -d)
  report="$ROOT/skills/implement/scripts/stall-recovery-report.sh"
  stage_terminal "$d" failed-clarify clarify clarify-loop clarify-loop failed clarify-hard-halt clarify-loop
  printf '%s\n' "$marker" >"$d/$leak_file"
  : >"$d/design-failure-classification.seed.env"
  : >"$d/design-failure-attempts.env"
  cat >"$d/design-failure-root-cause.md" <<EOF2
verdict=larch-defect
confidence=medium
summary=bounded summary includes $marker

Bounded root cause only.
EOF2
  cp "$d/design-failure-root-cause.md" "$d/design-failure-bounded-root-cause.md"
  if CLAUDE_PROJECT_DIR="$consumer" "$report" --profile generic --artifact-prefix design-failure \
    --implement-tmpdir "$d" populate-sensitive-corpus \
    --sensitive-corpus-file "$d/design-failure-sensitive-corpus.env" \
    --classification-file "$d/design-failure-classification.seed.env" \
    --attempts-file "$d/design-failure-attempts.env" >/dev/null 2>"$d/populate.stderr"; then
    :
  else
    fail "$label: populate-sensitive-corpus failed"
  fi
  if CLAUDE_PROJECT_DIR="$consumer" "$report" --profile generic --artifact-prefix design-failure \
    --implement-tmpdir "$d" --primary-state-file "$d/design-failure-terminal-state.env" \
    compose-report --report-kind terminal-failure --surface chat-print \
    --classification-file "$d/design-failure-classification.seed.env" \
    --attempts-file "$d/design-failure-attempts.env" \
    --root-cause-file "$d/design-failure-root-cause.md" \
    --bounded-root-cause-file "$d/design-failure-bounded-root-cause.md" \
    --sensitive-corpus-file "$d/design-failure-sensitive-corpus.env" \
    --output-file "$d/design-failure-chat-print.md" >"$d/compose.env" 2>"$d/compose.stderr"; then
    fail "$label: compose-report should reject sensitive leak"
  fi
  if [ -s "$d/design-failure-chat-print.md" ] && grep -Fq "$marker" "$d/design-failure-chat-print.md"; then
    fail "$label: marker leaked into chat-print"
  fi
  pass "$label: sensitive corpus blocks leak"
}

assert_sensitive_leak_blocked 'issue-body.txt leak' issue-body.txt 'unique-leak-marker-issue-body-99'
assert_sensitive_leak_blocked 'feature-description.txt leak' feature-description.txt 'unique-leak-marker-feature-description-88'
assert_sensitive_leak_blocked 'source-env.sh leak' source-env.sh 'unique-leak-marker-source-env-77'

printf 'PASS: test-design-failure-report.sh\n'
