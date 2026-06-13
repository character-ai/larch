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
grep -Fxq 'PRESERVED=true' "$D5/preserve.out" || fail 'different terminal state was not preserved'
grep -Fxq 'FAILURE_OUTCOME=failed-clarify' "$D5/design-failure-terminal-state.env" || fail 'different state overwritten'
pass 'preserves existing different terminal state'
