#!/usr/bin/env bash
# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILL_MD="$ROOT/skills/design/SKILL.md"
BRAINSTORM_MD="$ROOT/skills/design/references/brainstorm.md"
CLI_PY="$ROOT/python/cli.py"
DESIGN_LIFECYCLE="$ROOT/python/design_lifecycle.py"
SESSION_ENV="$ROOT/python/session_env.py"
MIGRATED="$ROOT/python/migrated-scripts.tsv"
MAKEFILE="$ROOT/Makefile"
STEP3B_ENTRY="$ROOT/skills/design/scripts/design-step3b-entry.sh"

fail() { printf '%s\n' "$1" >&2; exit 1; }
contains() {
  file="$1"
  literal="$2"
  label="$3"
  # -e marks the literal as the pattern so values starting with '-' (e.g.
  # '--with-plan-size') are not parsed as grep options.
  ( command grep -Fq -e "$literal" "$file" ) || fail "$label"
}
not_contains() {
  file="$1"
  literal="$2"
  label="$3"
  if ( command grep -Fq -e "$literal" "$file" ); then
    fail "$label"
  fi
}
assert_step3b_classifier() {
  expected="$1"
  plan_text="$2"
  label="$3"
  tmpdir="$(mktemp -d)"
  printf '%s\n' "$plan_text" > "$tmpdir/plan.txt"
  sed '/^case "\${MODE:-}" in/,$d' "$STEP3B_ENTRY" > "$tmpdir/step3b-entry-source.sh"
  actual="$(
    DESIGN_TMPDIR="$tmpdir" CLAUDE_PLUGIN_ROOT="$ROOT" bash -c \
      'set -euo pipefail; . "$1" --; classify_diagram_required' \
      _ "$tmpdir/step3b-entry-source.sh"
  )"
  rm -rf "$tmpdir"
  [ "$actual" = "$expected" ] || fail "$label: expected $expected got $actual"
}

ported_verbs='step0-parse step0-session step0-route step0-clarify-hard-halt step0-init step0-abort-cleanup step0-ap-continue step0c step1d5 step1d7 step1e-reentry'
retired_paths='design-step0-parse.sh design-step0-session.sh design-step0-route.sh design-step0-clarify-hard-halt.sh design-step0-init.sh design-step0-abort-cleanup.sh design-step0-ap-continue.sh design-step0c.sh design-step1d5.sh design-step1d7.sh design-step1e-reentry.sh test-design-step0-init.sh test-design-step1d5.sh'

contains "$SKILL_MD" 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" design step0-session' 'Step 0 session fence must call direct Python verb'
contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step0-route --issue-number "${ISSUE_NUMBER:-}"' 'Step 0 route fence must use bare launcher verb'
contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step1d5 --mode entry' 'Step 1d.5 entry must use bare launcher verb'
contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step1e-reentry' 'Step 1e reentry must use bare launcher verb'
contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-clarify.sh --phase fetch --issue "$ISSUE_NUMBER"' 'Clarify must stay on .sh launcher branch'
contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step2a.sh' 'Step 2+ wrappers must stay on .sh launcher branch'

for retired in $retired_paths; do
  not_contains "$SKILL_MD" "$retired" "SKILL.md still references retired $retired"
  [ ! -e "$ROOT/skills/design/scripts/$retired" ] || fail "retired script still exists: $retired"
  contains "$MIGRATED" "skills/design/scripts/$retired" "migrated-scripts.tsv missing $retired"
done

stdout_keys_block="$(awk '/^_DESIGN_LIFECYCLE_STDOUT_KEYS:/{flag=1;next}/^\)/{if(flag){flag=0}}flag' "$CLI_PY")"
for verb in $ported_verbs; do
  contains "$CLI_PY" "(\"design\", \"$verb\")" "cli registry missing design $verb"
  contains "$SESSION_ENV" "$verb" "design launcher missing $verb allowlist token"
  printf '%s' "$stdout_keys_block" | grep -Fq "(\"design\", \"$verb\")" || fail "cli _DESIGN_LIFECYCLE_STDOUT_KEYS missing design $verb"
done

contains "$SESSION_ENV" 'exec python3 "$PLUGIN_ROOT/python/cli.py" design "$script" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' 'launcher must dispatch ported verbs to python/cli.py'
contains "$SESSION_ENV" 'exec "$PLUGIN_ROOT/skills/design/scripts/$script" --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' 'launcher must preserve .sh dispatch'
contains "$SESSION_ENV" 'ERROR=unknown design wrapper verb' 'launcher must reject unlisted non-.sh tokens'
contains "$SESSION_ENV" 'ERROR=ported design wrapper must use bare verb name, not .sh' 'launcher must reject retired .sh token spellings'

contains "$DESIGN_LIFECYCLE" 'step0-parsed-' 'Step 0 parse must persist parsed env cache'
contains "$DESIGN_LIFECYCLE" 'POSITIONAL_VALUE={data.get' 'Step 0 parse must emit positional value'
contains "$DESIGN_LIFECYCLE" 'skill loader did not expand public argv words' 'Step 0 parse validation must reject unexpanded argv template'
contains "$DESIGN_LIFECYCLE" 'BOTH_DOWN_SEEN' 'Degraded gate relay must track BOTH_DOWN_SEEN'
contains "$DESIGN_LIFECYCLE" 'DEGRADED_EXPLANATION_BEGIN' 'Degraded gate relay must forward explanation block'
contains "$DESIGN_LIFECYCLE" 'CLAUDE_PLUGIN_ROOT' 'Wrapper verbs must export plugin root before subprocesses'
contains "$DESIGN_LIFECYCLE" 'cancel-pause-load' 'Route wrapper must handle cancel-pause-load before success KVs'
contains "$DESIGN_LIFECYCLE" 'POSITIONAL_KIND=issue requires numeric POSITIONAL_VALUE' 'Route wrapper must re-validate positional issue binding'
contains "$DESIGN_LIFECYCLE" '.design-step0-route-state.env' 'Route wrapper must write route-state sidecar'
contains "$DESIGN_LIFECYCLE" '.design-route-result.env' 'Init wrapper must gate on route result env'
contains "$DESIGN_LIFECYCLE" 'design-init-runparams.sh exited 0 without INIT_STATUS=ok' 'Init wrapper must fail closed without ok result'
contains "$DESIGN_LIFECYCLE" 'stage_terminal_state_core' 'Clarify hard halt must stage terminal state in-process'
contains "$CLI_PY" '("design", "stage-terminal-state")' 'CLI must register design stage-terminal-state'
contains "$CLI_PY" '("design", "failure-report")' 'CLI must register design failure-report'
contains "$CLI_PY" '("design", "step-final-summary")' 'CLI must register design step-final-summary'
contains "$SESSION_ENV" 'design stage-terminal-state "$@"' 'launcher must map stage terminal basename to CLI'
contains "$SESSION_ENV" 'design failure-report "$@"' 'launcher must map failure report basename to CLI'
contains "$SESSION_ENV" 'design step-final-summary --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' 'launcher must map final summary basename to CLI'
contains "$DESIGN_LIFECYCLE" '.brainstorm-{log_path.name}.runlog-appended' 'Brainstorm launch failure append must be idempotent'
contains "$DESIGN_LIFECYCLE" 'step-2a.5' 'Step 1e reentry must clear step-2a.5 sentinel'
contains "$DESIGN_LIFECYCLE" 'step-0c' 'Step 0c sentinel contract must remain pinned'

contains "$BRAINSTORM_MD" 'timeout: 1260000' 'Brainstorm collect docs must pin foreground Bash timeout'
contains "$BRAINSTORM_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step1d5 --mode collect --' 'Brainstorm collect must use launcher-owned collect verb'
not_contains "$BRAINSTORM_MD" 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent collect-results --timeout 1260' 'Brainstorm docs must not call collect-results directly'
not_contains "$BRAINSTORM_MD" '## Post-collection dirty-tree checkpoint' 'Brainstorm docs must drop standalone dirty-tree checkpoint section'

contains "$MAKEFILE" 'python3 -m pytest python/test_design_lifecycle.py' 'Make targets must route retired shell harnesses to pytest'

g6_terminal_retired_paths='design-stage-terminal-state.sh design-stage-terminal-state.md test-design-stage-terminal-state.sh test-design-stage-terminal-state.md design-failure-report.sh design-failure-report.md test-design-failure-report.sh test-design-failure-report.md design-step-final-summary.sh design-step-final-summary.md _dbg-stage.sh _debug-step5c.sh'
for retired in $g6_terminal_retired_paths; do
  [ ! -e "$ROOT/skills/design/scripts/$retired" ] || fail "retired G6.2 script still exists: $retired"
  contains "$MIGRATED" "skills/design/scripts/$retired" "migrated-scripts.tsv missing $retired"
done
debug_step5c_once='debug-step5c-once.sh'
[ ! -e "$ROOT/scripts/$debug_step5c_once" ] || fail "retired G6.2 script still exists: scripts/$debug_step5c_once"
contains "$MIGRATED" "scripts/$debug_step5c_once" "migrated-scripts.tsv missing scripts/$debug_step5c_once"

step2_verbs='step2a step2b-drafter step2b-postplan step2b5'
step2_retired_paths='design-step2a.sh design-step2a.md design-step2b-drafter.sh design-step2b-drafter.md design-step2b-postplan.sh design-step2b-postplan.md design-step2b5.sh design-step2b5.md design-step-validator-autofix.sh design-step-validator-autofix.md design-step2b-prelude.sh design-step2b-prelude.md test-design-step2b-drafter.sh test-design-step2b-drafter.md test-design-step-validator-autofix.sh test-design-step-validator-autofix.md'
SETTLE_SH="$ROOT/skills/design/scripts/design-step35-settle.sh"
SETTLE_MD="$ROOT/skills/design/scripts/design-step35-settle.md"
DESIGN_POSTPLAN="$ROOT/python/design_postplan.py"

for verb in $step2_verbs; do
  contains "$CLI_PY" "(\"design\", \"$verb\")" "cli registry missing design $verb"
  printf '%s' "$stdout_keys_block" | grep -Fq "(\"design\", \"$verb\")" || fail "cli _DESIGN_LIFECYCLE_STDOUT_KEYS missing design $verb"
done
contains "$CLI_PY" '("plan", "validator-autofix")' 'cli registry missing plan validator-autofix'

for retired in $step2_retired_paths; do
  [ ! -e "$ROOT/skills/design/scripts/$retired" ] || fail "retired Step 2 script still exists: $retired"
  contains "$MIGRATED" "skills/design/scripts/$retired" "migrated-scripts.tsv missing $retired"
done

contains "$SESSION_ENV" 'design-step2a.sh)' 'launcher must map design-step2a.sh'
contains "$SESSION_ENV" 'design step2a --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' 'launcher must forward step2a to python/cli.py'
contains "$SESSION_ENV" 'design-step2b-drafter.sh)' 'launcher must map design-step2b-drafter.sh'
contains "$SESSION_ENV" 'design step2b-drafter --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' 'launcher must forward step2b-drafter to python/cli.py'
contains "$SESSION_ENV" 'design-step2b-postplan.sh)' 'launcher must map design-step2b-postplan.sh'
contains "$SESSION_ENV" 'design step2b-postplan --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' 'launcher must forward step2b-postplan to python/cli.py'
contains "$SESSION_ENV" 'design-step2b5.sh)' 'launcher must map design-step2b5.sh'
contains "$SESSION_ENV" 'design step2b5 --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' 'launcher must forward step2b5 to python/cli.py'
contains "$SESSION_ENV" 'design-step-validator-autofix.sh)' 'launcher must map design-step-validator-autofix.sh'
contains "$SESSION_ENV" 'plan validator-autofix --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' 'launcher must forward validator-autofix to python/cli.py'

contains "$DESIGN_LIFECYCLE" '_shared_step2b_postplan_body' 'Step 2 postplan must use shared body helper'
contains "$DESIGN_LIFECYCLE" 'postplan_emit_main' 'Step 2 postplan must delegate to postplan_emit_main'
contains "$DESIGN_LIFECYCLE" '--with-plan-size' 'Step 2 postplan must call with-plan-size'
contains "$DESIGN_LIFECYCLE" 'POSTPLAN_RC=' 'Step 2 postplan must emit POSTPLAN_RC rows'
contains "$DESIGN_LIFECYCLE" 'POSTPLAN_STATUS=' 'Step 2 postplan must emit POSTPLAN_STATUS rows'
contains "$DESIGN_LIFECYCLE" '_call_pause_save' 'Step 2 postplan must thread pause-save helper'
contains "$DESIGN_LIFECYCLE" '.step2b-postplan-fallback-used' 'Step 2 drafter must seed fallback-used sentinel'
contains "$DESIGN_LIFECYCLE" 'drafter subprocess succeeded' 'Step 2 drafter must emit human success line'
contains "$DESIGN_LIFECYCLE" 'DRAFTER_STATUS=succeeded' 'Step 2 drafter must emit DRAFTER_STATUS=succeeded after postplan'
contains "$DESIGN_LIFECYCLE" 'snapshot_original=True' 'Step 2 drafter must delegate postplan with snapshot-original'
contains "$DESIGN_LIFECYCLE" '_valid_step2b_sentinels' 'Step 2 drafter must validate Step 2a sentinels in-process'
contains "$DESIGN_POSTPLAN" 'DRIFT_TRIGGER_FIRED' 'design_postplan must parse drift trigger'
contains "$DESIGN_POSTPLAN" 'BASELINE_PLAN_LINES' 'design_postplan must parse drift baseline'

assert_step3b_classifier false $'## Files to modify/create\n### MAY_UPDATE: docs/issue-anchored-plan.md' 'MAY_UPDATE docs path must not require diagram'
assert_step3b_classifier false $'## Files to modify/create\n### MAY_UPDATE: `docs/issue-anchored-plan.md`' 'MAY_UPDATE backtick docs path must not require diagram'
assert_step3b_classifier true $'## Files to modify/create\n### MAY_UPDATE: skills/design/scripts/foo.sh' 'MAY_UPDATE script path must require diagram'

contains "$SETTLE_SH" 'python/cli.py" design step2b-postplan' 'settle must default to python/cli.py design step2b-postplan'
contains "$SETTLE_SH" '--site "$POSTPLAN_SITE"' 'settle must pass mapped postplan site'
contains "$SETTLE_SH" '"${PUBLIC_ARGV_WORDS[@]}"' 'settle must forward caller tail after --'
contains "$SETTLE_MD" 'python/cli.py design step2b-postplan --site gate-b' 'settle doc must name gate-b postplan authority'
contains "$SETTLE_MD" 'python/cli.py design step2b-postplan --site discussion-round2' 'settle doc must name discussion postplan authority'
contains "$SETTLE_MD" 'python/test_design_lifecycle.py' 'settle doc must name pytest structure coverage'

contains "$SKILL_MD" 'python/cli.py design step2b-drafter' 'SKILL must name step2b-drafter Python authority'
contains "$SKILL_MD" 'python/cli.py design step2b-postplan' 'SKILL must name step2b-postplan Python authority'

step6_verbs='step6 step6-prelude step6-cleanup'
step6_retired_paths='design-step6.sh design-step6.md design-step6-prelude.sh design-step6-prelude.md design-step6-cleanup.sh design-step6-cleanup.md test-design-step6.sh _dbg-validator.sh _dbg5c2.sh'

for verb in $step6_verbs; do
  contains "$CLI_PY" "(\"design\", \"$verb\")" "cli registry missing design $verb"
  printf '%s' "$stdout_keys_block" | grep -Fq "(\"design\", \"$verb\")" || fail "cli _DESIGN_LIFECYCLE_STDOUT_KEYS missing design $verb"
  contains "$SESSION_ENV" "$verb" "design launcher missing $verb allowlist token"
done

for retired in $step6_retired_paths; do
  [ ! -e "$ROOT/skills/design/scripts/$retired" ] || fail "retired Step 6 script still exists: $retired"
  contains "$MIGRATED" "skills/design/scripts/$retired" "migrated-scripts.tsv missing $retired"
  not_contains "$SKILL_MD" "$retired" "SKILL.md still references retired $retired"
done

contains "$SESSION_ENV" 'design-step6.sh)' 'launcher must map design-step6.sh'
contains "$SESSION_ENV" 'design step6 --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' 'launcher must forward step6 to python/cli.py'
contains "$SESSION_ENV" 'design-step6-prelude.sh)' 'launcher must map design-step6-prelude.sh'
contains "$SESSION_ENV" 'design step6-prelude --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' 'launcher must forward step6-prelude to python/cli.py'
contains "$SESSION_ENV" 'design-step6-cleanup.sh)' 'launcher must map design-step6-cleanup.sh'
contains "$SESSION_ENV" 'design step6-cleanup --session-env-path "$SESSION_ENV_PATH" --claude-pid "$CLAUDE_PID" "$@"' 'launcher must forward step6-cleanup to python/cli.py'
contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step6' 'SKILL Step 6 fence must use bare launcher verb'

printf '%s\n' 'test-design-structure: ok'
