#!/usr/bin/env bash
# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILL_MD="$ROOT/skills/design/SKILL.md"
BRAINSTORM_MD="$ROOT/skills/design/references/brainstorm.md"
APPROVAL_GATES_MD="$ROOT/skills/design/references/approval-gates.md"
DISCUSSION_ROUNDS_MD="$ROOT/skills/design/references/discussion-rounds.md"
SETTLE_DISPATCH_MD="$ROOT/skills/design/references/settle-rc-dispatch.md"
OOS_STEP5B_DISPATCH_MD="$ROOT/skills/design/references/oos-step5b-dispatch.md"
CLI_PY="$ROOT/python/cli.py"
DESIGN_LIFECYCLE="$ROOT/python/design_lifecycle.py"
SESSION_ENV="$ROOT/python/session_env.py"
MIGRATED="$ROOT/python/migrated-scripts.tsv"
MAKEFILE="$ROOT/Makefile"
STEP3B_ENTRY="$ROOT/skills/design/scripts/design-step3b-entry.sh"
STEP3B_SANITIZE="$ROOT/skills/design/scripts/design-step3b-sanitize.sh"

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
assert_followed_count_at_least() {
  file="$1"
  first="$2"
  second="$3"
  expected="$4"
  label="$5"
  actual="$(
    awk -v first="$first" -v second="$second" '
      $0 == first {
        if ((getline next_line) > 0 && next_line == second) {
          count++
        }
      }
      END { print count + 0 }
    ' "$file"
  )"
  [ "$actual" -ge "$expected" ] || fail "$label: expected at least $expected adjacent pair(s), found $actual"
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
contains "$DESIGN_LIFECYCLE" '"OOS_SKIP_BREADCRUMB",' 'phase result allowlist must include OOS skip breadcrumb'
contains "$DESIGN_LIFECYCLE" '"SETTLE_NEXT_ACTION",' 'phase result allowlist must include settle next action'

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

contains "$SKILL_MD" '1c→1d→1d.5→1d.7→2a→2b→2b.5→3→3.5→3b→4→4b→5→5b→5b.5→5c.1→5c.5→5c.7→5c.8→6' 'anti-halt chain must include Step 5b.5 before Step 5c'
contains "$SKILL_MD" 'design-step3b-entry.sh --mode finalize' 'Step 3b must use finalize mode'
contains "$SKILL_MD" 'design-step3b-entry.sh --mode diagram' 'Step 5b.5 must use diagram mode'
contains "$STEP3B_ENTRY" '.completed/step-4' 'diagram mode must require step-4 sentinel'
contains "$STEP3B_ENTRY" '.completed/step-5b' 'diagram mode must require step-5b sentinel'
contains "$SKILL_MD" 'Append only a bounded warning to `execution-issues.md` via `design_diagram_log.write_bounded_diagram_failure_log`' 'Step 5b.5 generation failure must use bounded warning logging'
contains "$SKILL_MD" 'Step 5b.5 diagram generation and sanitizer rejection paths append bounded' 'Step 5b.5 must not use full-capture append-failure for diagram paths'
contains "$SKILL_MD" 'architecture diagram content is issue-only via `larch:diagrams`' 'SKILL verbosity must not authorize architecture diagram chat emission'
contains "$SKILL_MD" 'Continue to Step 5b.5 IMMEDIATELY' 'Step 5b must continue to Step 5b.5 before Step 5c'
contains "$SKILL_MD" 'Parse `NEXT_ACTION=` from `$DESIGN_TMPDIR/oos-filing-prepare.env`' 'Step 5b prose must branch on NEXT_ACTION'
contains "$SKILL_MD" 'NEXT_ACTION=unknown-oos-status' 'Step 5b must special-case unknown-oos-status on non-zero prepare rc'
contains "$SKILL_MD" 'stop for repair' 'Step 5b must stop for repair on unknown OOS status'
contains "$OOS_STEP5B_DISPATCH_MD" 'unknown-oos-status' 'oos step5b dispatch must document unknown-oos-status repair stop'
contains "$SKILL_MD" 'call `design-step5b-annotate.sh` only when `$DESIGN_TMPDIR/oos-issue.stdout.txt` exists and is non-empty' 'skip-already-filed must retain stdout-non-empty annotate guard'
contains "$SKILL_MD" 'tool `python/cli.py design file-oos-prepare`, category `Warnings`, exit code 0' 'skip-already-filed must append WARN rows as warnings'
contains "$SKILL_MD" 'Prepare already wrote `.completed/step-5b` for `skip-already-filed-sentinel` without annotate.' 'skip-already-filed without annotate must rely on prepare completion marker'
contains "$SKILL_MD" 'skills/design/references/oos-step5b-dispatch.md' 'Step 5b must reference oos-step5b dispatch fallback'
assert_followed_count_at_least "$SKILL_MD" '     1. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/oos-step5b-dispatch.md` completely.' '     2. Parse `NEXT_ACTION=` from `$DESIGN_TMPDIR/oos-filing-prepare.env` (ignore unrelated lines). When `NEXT_ACTION` is missing, derive it from `FILE_DESIGN_OOS_STATUS=` using the fallback table in `oos-step5b-dispatch.md`. If the fallback status is unknown, stop for repair. If `NEXT_ACTION` and the status-derived action disagree, stop for repair.' 1 'SKILL Step 5b must load oos-step5b dispatch immediately before branch directive'
[ -f "$OOS_STEP5B_DISPATCH_MD" ] || fail "oos step5b dispatch reference missing"
grep -Eq '^\*\*When to load\*\*:' "$OOS_STEP5B_DISPATCH_MD" || fail "oos step5b dispatch must anchor When to load header"
contains "$OOS_STEP5B_DISPATCH_MD" 'Primary key: branch on the whole-line `NEXT_ACTION=...` row from `oos-filing-prepare.env`' 'oos step5b dispatch must name primary NEXT_ACTION key'
contains "$OOS_STEP5B_DISPATCH_MD" 'Fallback key: when the action row is missing, parse `FILE_DESIGN_OOS_STATUS=` from `oos-filing-prepare.env`' 'oos step5b dispatch must retain FILE_DESIGN_OOS_STATUS fallback'
contains "$OOS_STEP5B_DISPATCH_MD" 'If `NEXT_ACTION` and the status-derived action disagree, stop for repair rather than silently choosing one.' 'oos step5b dispatch must stop on action status disagreement'
contains "$OOS_STEP5B_DISPATCH_MD" '| `skip-sentinel` |' 'oos step5b dispatch must document skip-sentinel'
contains "$OOS_STEP5B_DISPATCH_MD" '| `skip-already-filed-sentinel` |' 'oos step5b dispatch must document skip-already-filed-sentinel'
contains "$OOS_STEP5B_DISPATCH_MD" '| `skip-no-items` |' 'oos step5b dispatch must document skip-no-items'
contains "$OOS_STEP5B_DISPATCH_MD" '| `skip-all-security` |' 'oos step5b dispatch must document skip-all-security'
contains "$OOS_STEP5B_DISPATCH_MD" '| `ready` |' 'oos step5b dispatch must document ready'
contains "$OOS_STEP5B_DISPATCH_MD" '## Fallback: branch on FILE_DESIGN_OOS_STATUS' 'canonical oos step5b dispatch must own the status fallback phrase'
contains "$SKILL_MD" 'architecture diagram work runs only at Step 5b.5 after Gate C approval' 'Step 2b anti-halt must not promise pre-approval diagram generation'
contains "$STEP3B_SANITIZE" 'architecture-diagram.skipped' 'sanitizer fail-closed paths must touch skipped marker'
contains "$STEP3B_SANITIZE" 'design Step 5b.5' 'sanitizer warning site must name Step 5b.5'
not_contains "$STEP3B_SANITIZE" 'LARCH-DIAGRAM' 'sanitizer must not emit chat diagram markers'
not_contains "$SKILL_MD" 're-emit that exact body verbatim in chat' 'SKILL must not instruct diagram body re-emission'

contains "$SETTLE_SH" 'python/cli.py" design step2b-postplan' 'settle must default to python/cli.py design step2b-postplan'
contains "$SETTLE_SH" '--site "$POSTPLAN_SITE"' 'settle must pass mapped postplan site'
contains "$SETTLE_SH" '"${PUBLIC_ARGV_WORDS[@]}"' 'settle must forward caller tail after --'
contains "$SETTLE_MD" 'python/cli.py design step2b-postplan --site gate-b' 'settle doc must name gate-b postplan authority'
contains "$SETTLE_MD" 'python/cli.py design step2b-postplan --site discussion-round2' 'settle doc must name discussion postplan authority'
contains "$SETTLE_MD" 'python/test_design_lifecycle.py' 'settle doc must name pytest structure coverage'

[ -f "$SETTLE_DISPATCH_MD" ] || fail "settle rc dispatch reference missing"
grep -Eq '^\*\*When to load\*\*:' "$SETTLE_DISPATCH_MD" || fail "settle rc dispatch must anchor When to load header"
contains "$SETTLE_DISPATCH_MD" 'Primary key: branch on the whole-line `SETTLE_NEXT_ACTION=...` row from `design-step35-settle.sh` stdout.' 'settle dispatch must name primary SETTLE_NEXT_ACTION key'
contains "$SETTLE_DISPATCH_MD" 'Fallback key: when the action row is missing, branch on the `design-step35-settle.sh` process exit status (`$?` after the launcher fence).' 'settle dispatch must retain wrapper rc fallback'
contains "$SETTLE_DISPATCH_MD" 'If `SETTLE_NEXT_ACTION` and wrapper rc disagree, stop for repair rather than silently choosing one.' 'settle dispatch must stop on action rc disagreement'
contains "$SETTLE_DISPATCH_MD" 'There is no `POSTPLAN_RC=1` on the postplan path.' 'settle rc dispatch must reject POSTPLAN_RC=1 wording'
contains "$SETTLE_DISPATCH_MD" '| `0` |' 'settle rc dispatch must document rc 0'
contains "$SETTLE_DISPATCH_MD" '| `1` |' 'settle rc dispatch must document rc 1'
contains "$SETTLE_DISPATCH_MD" '| `10` |' 'settle rc dispatch must document rc 10'
contains "$SETTLE_DISPATCH_MD" '| `11` |' 'settle rc dispatch must document rc 11'
contains "$SETTLE_DISPATCH_MD" '| `12` |' 'settle rc dispatch must document rc 12'
contains "$SETTLE_DISPATCH_MD" '| `13` |' 'settle rc dispatch must document rc 13'
contains "$SETTLE_DISPATCH_MD" '| Other non-zero |' 'settle rc dispatch must document other non-zero'
contains "$SETTLE_DISPATCH_MD" '| **Gate B** |' 'settle rc dispatch must document Gate B variant'
contains "$SETTLE_DISPATCH_MD" '| **Gate A / discussion-round2** |' 'settle rc dispatch must document Gate A / discussion-round2 variant'

for caller in "$SKILL_MD" "$APPROVAL_GATES_MD" "$DISCUSSION_ROUNDS_MD"; do
  contains "$caller" 'skills/design/references/settle-rc-dispatch.md' "caller must reference settle rc dispatch: $caller"
done
assert_followed_count_at_least "$APPROVAL_GATES_MD" '   1. **MANDATORY — READ ENTIRE FILE**: Read `skills/design/references/settle-rc-dispatch.md` completely.' '   2. Branch on `SETTLE_NEXT_ACTION` when present. Use the **Gate B** fallback row only when the action row is missing. If the action row and wrapper rc disagree, stop for repair. Map `gate-b-validator-fail` to the existing rc `10` Gate B behavior: read the allowlisted env, execute the shared validator flow, and offer retry / override / cancel.' 1 'approval-gates must load settle dispatch immediately before Gate B branch directive'
assert_followed_count_at_least "$DISCUSSION_ROUNDS_MD" '1. **MANDATORY — READ ENTIRE FILE**: Read `skills/design/references/settle-rc-dispatch.md` completely.' '2. Branch on `SETTLE_NEXT_ACTION` when present. Use the **Gate A / discussion-round2** fallback row only when the action row is missing. Map `gate-a-validator-fail`, `gate-a-hard-size`, and `gate-a-split` to the existing rc `10` / `12` / `13` Gate A or discussion-round2 behavior, including shared validator prompts for validator-fail.' 1 'discussion-rounds must use numbered settle dispatch steps 1-2'
assert_followed_count_at_least "$SKILL_MD" '1. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/settle-rc-dispatch.md` completely.' '2. Branch on `SETTLE_NEXT_ACTION` when present. Use the **Gate A / discussion-round2** fallback row only when the action row is missing. If the action row and wrapper rc disagree, stop for repair.' 1 'SKILL Gate A guard must load settle dispatch immediately before branch directive'
assert_followed_count_at_least "$SKILL_MD" '1. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/settle-rc-dispatch.md` completely.' '2. Branch on `SETTLE_NEXT_ACTION` when present. Use the **Gate B** fallback row only when the action row is missing. If the action row and wrapper rc disagree, stop for repair.' 1 'SKILL Gate B guard must load settle dispatch immediately before branch directive'

not_contains "$APPROVAL_GATES_MD" 'Branch on the settle wrapper rc' 'approval-gates must not retain inline settle rc branch table'
not_contains "$APPROVAL_GATES_MD" 'Branch on wrapper rc' 'approval-gates must not retain inline wrapper rc branch table'
not_contains "$DISCUSSION_ROUNDS_MD" 'Branch on the settle wrapper rc' 'discussion-rounds must not retain inline settle rc branch table'
not_contains "$DISCUSSION_ROUNDS_MD" 'Branch on wrapper rc' 'discussion-rounds must not retain inline wrapper rc branch table'
not_contains "$SKILL_MD" 'Branch on the settle wrapper rc' 'SKILL must not retain inline settle rc branch table'
not_contains "$SKILL_MD" 'Branch on wrapper rc' 'SKILL must not retain inline wrapper rc branch table'
contains "$SETTLE_DISPATCH_MD" '## Fallback: branch on wrapper rc' 'canonical settle dispatch must own the wrapper rc fallback phrase'

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
