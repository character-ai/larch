#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILL_MD="$ROOT/skills/design/SKILL.md"
BRAINSTORM_MD="$ROOT/skills/design/references/brainstorm.md"
CLI_PY="$ROOT/python/cli.py"
DESIGN_LIFECYCLE="$ROOT/python/design_lifecycle.py"
SESSION_ENV="$ROOT/python/session_env.py"
MIGRATED="$ROOT/python/migrated-scripts.tsv"
MAKEFILE="$ROOT/Makefile"

fail() { printf '%s\n' "$1" >&2; exit 1; }
contains() {
  file="$1"
  literal="$2"
  label="$3"
  ( command grep -Fq "$literal" "$file" ) || fail "$label"
}
not_contains() {
  file="$1"
  literal="$2"
  label="$3"
  if ( command grep -Fq "$literal" "$file" ); then
    fail "$label"
  fi
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

for verb in $ported_verbs; do
  contains "$CLI_PY" "(\"design\", \"$verb\")" "cli registry missing design $verb"
  contains "$SESSION_ENV" "$verb" "design launcher missing $verb allowlist token"
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
contains "$DESIGN_LIFECYCLE" 'design-stage-terminal-state.sh' 'Clarify hard halt must stage terminal state'
contains "$DESIGN_LIFECYCLE" '.brainstorm-{log_path.name}.runlog-appended' 'Brainstorm launch failure append must be idempotent'
contains "$DESIGN_LIFECYCLE" 'step-2a.5' 'Step 1e reentry must clear step-2a.5 sentinel'
contains "$DESIGN_LIFECYCLE" 'step-0c' 'Step 0c sentinel contract must remain pinned'

contains "$BRAINSTORM_MD" 'timeout: 1260000' 'Brainstorm collect docs must pin foreground Bash timeout'
contains "$BRAINSTORM_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step1d5 --mode collect --' 'Brainstorm collect must use launcher-owned collect verb'
not_contains "$BRAINSTORM_MD" 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent collect-results --timeout 1260' 'Brainstorm docs must not call collect-results directly'
not_contains "$BRAINSTORM_MD" '## Post-collection dirty-tree checkpoint' 'Brainstorm docs must drop standalone dirty-tree checkpoint section'

contains "$MAKEFILE" 'python3 -m pytest python/test_design_lifecycle.py' 'Make targets must route retired shell harnesses to pytest'

printf '%s\n' 'test-design-structure: ok'
