#!/usr/bin/env bash
# test-design-stage-terminal-state.sh — offline harness for design-stage-terminal-state.sh.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SUBJECT="$ROOT/skills/design/scripts/design-stage-terminal-state.sh"
fail() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
pass() { printf 'PASS: %s\n' "$*"; }

D=$(mktemp -d)
trap 'rm -rf "$D"' EXIT

env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D" --outcome failed-clarify --step clarify --phase clarify-loop --site clarify-loop --trigger failed --bail-reason clarify-hard-halt --exit-code 1 --source-script clarify-loop >"$D/stdout"
for key in DESIGN_FAILURE_VERSION DESIGN_FAILURE_KIND FAILURE_OUTCOME STALL_STEP PHASE SITE TRIGGER BAIL_REASON EXIT_CODE FAILURE_DETAIL_LOG SOURCE_SCRIPT OCCURRED_AT; do
  grep -q "^$key=" "$D/design-failure-terminal-state.env" || fail "missing $key"
done
grep -Fxq 'FAILURE_OUTCOME=failed-clarify' "$D/design-failure-terminal-state.env" || fail 'failed-clarify not staged'
grep -Eq '^(STAGED|TERMINAL_STATE_FILE)=' "$D/stdout" || fail 'stdout must be KV-shaped'
pass 'stages failed-clarify with required keys'

D2=$(mktemp -d)
env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D2" --outcome failed-judge-panel --step judge-panel --phase judge-panel --site decompose-panel --trigger decompose-panel-retry-exhausted --bail-reason decompose-panel-retry-exhausted --exit-code 1 --source-script split-path >/dev/null
grep -Fxq 'SITE=decompose-panel' "$D2/design-failure-terminal-state.env" || fail 'decompose-panel site missing'
grep -Fxq 'TRIGGER=decompose-panel-retry-exhausted' "$D2/design-failure-terminal-state.env" || fail 'decompose-panel trigger missing'
pass 'stages failed-judge-panel from decompose-panel'

D3=$(mktemp -d)
if env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D3" --outcome bad-outcome --step clarify --phase clarify-loop --site clarify-loop --trigger failed --bail-reason clarify-hard-halt --exit-code 1 --source-script clarify-loop >/dev/null 2>&1; then
  fail 'unknown outcome accepted'
fi
if env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D3" --outcome failed-clarify --step nope --phase clarify-loop --site clarify-loop --trigger failed --bail-reason clarify-hard-halt --exit-code 1 --source-script clarify-loop >/dev/null 2>&1; then
  fail 'unknown design vocab accepted'
fi
pass 'rejects unknown outcome and vocab tokens'

D4=$(mktemp -d)
outside=$(mktemp)
if env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D4" --outcome failed-clarify --step clarify --phase clarify-loop --site clarify-loop --trigger failed --bail-reason clarify-hard-halt --exit-code 1 --source-script clarify-loop --failure-detail-log "$outside" >/dev/null 2>&1; then
  fail 'outside evidence accepted'
fi
inside="$D4/evidence.log"; printf 'safe\n' >"$inside"; ln -s "$inside" "$D4/evidence.link"
if env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D4" --outcome failed-clarify --step clarify --phase clarify-loop --site clarify-loop --trigger failed --bail-reason clarify-hard-halt --exit-code 1 --source-script clarify-loop --failure-detail-log "$D4/evidence.link" >/dev/null 2>&1; then
  fail 'symlink evidence accepted'
fi
pass 'rejects outside and symlink evidence paths'

D5=$(mktemp -d)
env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D5" --outcome failed-clarify --step clarify --phase clarify-loop --site clarify-loop --trigger failed --bail-reason clarify-hard-halt --exit-code 1 --source-script clarify-loop >/dev/null
env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D5" --outcome failed-publish --step publish --phase publish --site design-publish --trigger failed --bail-reason publish-failed --exit-code 1 --source-script design-publish >"$D5/preserve.out"
grep -Fxq 'STAGED=false' "$D5/preserve.out" || fail 'preserved different terminal state did not emit STAGED=false'
grep -Fxq 'PRESERVED=true' "$D5/preserve.out" || fail 'different terminal state was not preserved'
grep -Fxq 'FAILURE_OUTCOME=failed-clarify' "$D5/design-failure-terminal-state.env" || fail 'different state overwritten'
pass 'preserves existing different terminal state'

D6_PARENT="${HOME}/.cache/larch/sessions"
if ! mkdir -p "$D6_PARENT" 2>/dev/null || ! D6=$(mktemp -d "$D6_PARENT/larch-test-design-terminal.XXXXXX" 2>/dev/null); then
  D6=$(mktemp -d)
fi
D6=$(cd "$D6" && pwd -P)
trap 'rm -rf "$D" "$D2" "$D3" "$D4" "$D5" "$D6"' EXIT
inside_log="$D6/design-log-publish.failure.log"
printf 'publish failed\n' >"$inside_log"
env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D6" --outcome failed-publish --step publish --phase publish --site design-publish --trigger failed --bail-reason publish-failed --exit-code 1 --source-script design-publish --failure-detail-log "$inside_log" >/dev/null
grep -Fxq "FAILURE_DETAIL_LOG=$inside_log" "$D6/design-failure-terminal-state.env" || fail 'user-cache failure detail log rejected'
REPORT_SH="$ROOT/skills/implement/scripts/stall-recovery-report.sh"
env -u CLAUDE_PLUGIN_ROOT "$REPORT_SH" --profile generic --artifact-prefix design-failure --implement-tmpdir "$D6" validate-terminal-state --primary-state-file "$D6/design-failure-terminal-state.env" | grep -Fxq 'VALID=true' || fail 'validate-terminal-state rejected user-cache failure detail log'
pass 'accepts failure detail log under user-cache design tmpdir'

D7=$(mktemp -d)
D7_CANON=$(cd "$D7" && pwd -P)
inside_tail="$D7_CANON/design-publish-tail.failure.log"
printf 'publish tail failed\n' >"$inside_tail"
env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D7_CANON" --outcome failed-publish-tail --step publish --phase publish --site design-publish --trigger publish-tail-failed --bail-reason publish-tail-failed --exit-code 2 --source-script design-step5c --failure-detail-log "$inside_tail" --summary-outcome failed-publish-tail >/dev/null
grep -Fxq 'TRIGGER=publish-tail-failed' "$D7_CANON/design-failure-terminal-state.env" || fail 'publish-tail-failed trigger missing'
env -u CLAUDE_PLUGIN_ROOT "$REPORT_SH" --profile generic --artifact-prefix design-failure --implement-tmpdir "$D7_CANON" validate-terminal-state --primary-state-file "$D7_CANON/design-failure-terminal-state.env" | grep -Fxq 'VALID=true' || fail 'publish-tail terminal state invalid'
pass 'stages failed-publish-tail with publish-tail-failed trigger'

if D_DISALLOWED=$(mktemp -d "/var/tmp/larch-test-terminal-disallowed.XXXXXX" 2>/dev/null); then
  set +e
  env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D_DISALLOWED" --outcome failed-clarify --step clarify --phase clarify-loop --site clarify-loop --trigger failed --bail-reason clarify-hard-halt --exit-code 1 --source-script clarify-loop >"$D_DISALLOWED/out" 2>"$D_DISALLOWED/err"
  disallowed_rc=$?
  set -e
  [ "$disallowed_rc" -ne 0 ] || fail 'disallowed existing tmpdir accepted'
  grep -Fq 'allowlist' "$D_DISALLOWED/err" || fail 'disallowed stderr omitted allowlist rejection'
  if find "$D_DISALLOWED" -name 'larch-quiet-*.log' -print -quit | grep -q .; then
    fail 'quiet log created before disallowed tmpdir rejection'
  fi
  rm -rf "$D_DISALLOWED"
  pass 'rejects disallowed tmpdir before quiet init'
else
  pass 'skips disallowed tmpdir quiet-init check because /var/tmp is unavailable'
fi

D8=$(mktemp -d)
inside_panel="$D8/step3-panel-init-failed.log"
printf 'panel init failed\n' >"$inside_panel"
env -u CLAUDE_PLUGIN_ROOT "$SUBJECT" --design-tmpdir "$D8" --outcome failed-judge-panel --step judge-panel --phase judge-panel --site step3-review --trigger panel-init-failed --bail-reason panel-init-failed --exit-code 1 --source-script design-step3-review --failure-detail-log "$inside_panel" --summary-outcome failed-judge-panel >/dev/null
grep -Fxq 'BAIL_REASON=panel-init-failed' "$D8/design-failure-terminal-state.env" || fail 'panel-init-failed bail missing'
env -u CLAUDE_PLUGIN_ROOT "$REPORT_SH" --profile generic --artifact-prefix design-failure --implement-tmpdir "$D8" validate-token --token-kind bail --value panel-init-failed | grep -Fxq 'VALID=true' || fail 'panel-init-failed bail token invalid'
pass 'stages failed-judge-panel with panel-init-failed bail token'
