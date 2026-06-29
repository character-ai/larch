#!/usr/bin/env bash
# shellcheck disable=SC2016 # single-quoted strings are intentional grep literals
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILL_MD="$ROOT/skills/design/SKILL.md"
IMPL_MD="$ROOT/skills/implement/SKILL.md"
SHARED_DESIGN_WAIT_MD="$ROOT/skills/shared/design-background-wait.md"
ORCH_NEVER_MD="$ROOT/skills/shared/orchestrator-never.md"
BRAINSTORM_MD="$ROOT/skills/design/references/brainstorm.md"
APPROVAL_GATES_MD="$ROOT/skills/design/references/approval-gates.md"
DISCUSSION_ROUNDS_MD="$ROOT/skills/design/references/discussion-rounds.md"
SETTLE_DISPATCH_MD="$ROOT/skills/design/references/settle-rc-dispatch.md"
STEP2B5_RC_MD="$ROOT/skills/design/references/step2b5-rc-handling.md"
OOS_STEP5B_DISPATCH_MD="$ROOT/skills/design/references/oos-step5b-dispatch.md"
DIALECTIC_LEGACY_ATTIC_MD="$ROOT/docs/attic/dialectic-legacy.md"
FINALIZE_STEP5_MD="$ROOT/skills/design/references/finalize-step5.md"
CLI_PY="$ROOT/python/larch/cli.py"
# After the god-module split, design_lifecycle.py is a thin re-export shim.
# Combine all sub-modules so existing structural checks still find their strings.
_dl_combined="$(mktemp)"
cat \
  "$ROOT/python/larch/design/design_lifecycle.py" \
  "$ROOT/python/larch/design/design_core.py" \
  "$ROOT/python/larch/design/design_session.py" \
  "$ROOT/python/larch/design/design_terminal.py" \
  "$ROOT/python/larch/design/design_router.py" \
  "$ROOT/python/larch/design/design_step0_env.py" \
  "$ROOT/python/larch/design/design_step0.py" \
  "$ROOT/python/larch/design/design_step1.py" \
  "$ROOT/python/larch/design/design_step2b.py" \
  "$ROOT/python/larch/design/design_step5c.py" \
  "$ROOT/python/larch/design/design_step6.py" \
  "$ROOT/python/larch/design/design_step5b.py" \
  > "$_dl_combined"
DESIGN_LIFECYCLE="$_dl_combined"
# shellcheck disable=SC2064
trap "rm -f '$_dl_combined'" EXIT
SESSION_ENV="$ROOT/python/larch/state/session_env.py"
MIGRATED="$ROOT/python/migrated-scripts.tsv"
MAKEFILE="$ROOT/Makefile"
STEP3B_ENTRY="$ROOT/skills/design/scripts/design-step3b-entry.sh"
STEP3B_ENTRY_MD="$ROOT/skills/design/scripts/design-step3b-entry.md"
STEP3B_SANITIZE="$ROOT/skills/design/scripts/design-step3b-sanitize.sh"
LOAD_LITERAL='Read and apply ##'
CONFIRMATION_COMPLETION='confirmation purpose: completion'
CONFIRMATION_DURABLE_COMPLETION='confirmation purpose: durable completion'
WAIT_WHEN_ABSENT='`WAIT` when absent is expected'
RESUME_BACKREF_LITERAL='Use the same Step 3 task-notification, immediate-background, Parameters, post-notification, and terminal-sentinel contract as the first-time Step 3 review fence above.'
FINAL_SUMMARY_FENCE_ANCHOR='design-step-final-summary.sh --outcome'
STEP3_RESUME_ANCHOR='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-review.sh --starting-round'
STEP5C_ANCHOR='"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5c.sh'

fail() { printf '%s\n' "$1" >&2; exit 1; }

skill_lines=$(wc -l < "$SKILL_MD" | tr -d ' ')
[ "$skill_lines" -le 705 ] \
  || fail "skills/design/SKILL.md must stay <= 705 lines after prose compression (found $skill_lines)"

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
assert_line_precedes() {
  file="$1"
  early="$2"
  late="$3"
  label="$4"
  early_idx="$(awk -v needle="$early" '$0 == needle { print NR; exit }' "$file")"
  late_idx="$(awk -v needle="$late" '$0 == needle { print NR; exit }' "$file")"
  [ -n "$early_idx" ] || fail "$label: missing early needle"
  [ -n "$late_idx" ] || fail "$label: missing late needle"
  [ "$early_idx" -lt "$late_idx" ] || fail "$label: expected early line before late line (early=$early_idx late=$late_idx)"
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
context_after() {
  file="$1"
  anchor="$2"
  lines="$3"
  awk -v anchor="$anchor" -v max="$lines" '
    !seen && index($0, anchor) { found = 1; seen = 1; count = 0 }
    found && count < max { print; count++; if (count >= max) exit }
  ' "$file"
}
context_before() {
  file="$1"
  anchor="$2"
  lines="$3"
  awk -v anchor="$anchor" -v max="$lines" '
    { buf[NR] = $0 }
    END {
      for (i = 1; i <= NR; i++) {
        if (index(buf[i], anchor)) {
          start = i - max
          if (start < 1) start = 1
          for (j = start; j < i; j++) print buf[j]
          exit
        }
      }
    }
  ' "$file"
}
context_before_step3_launch() {
  file="$1"
  lines="$2"
  awk -v max="$lines" '
    { buf[NR] = $0 }
    END {
      for (i = 1; i <= NR; i++) {
        if (index(buf[i], "design-run-$PPID.sh\" design-step3-review.sh") && index(buf[i], "--starting-round") == 0) {
          start = i - max
          if (start < 1) start = 1
          for (j = start; j < i; j++) print buf[j]
          exit
        }
      }
    }
  ' "$file"
}
check_context() {
  file="$1"
  label="$2"
  anchor="$3"
  lines="$4"
  literal="$5"
  context="$(context_after "$file" "$anchor" "$lines")"
  printf '%s\n' "$context" | grep -Fq -e "$literal" || fail "$label"
}
check_context_before() {
  file="$1"
  label="$2"
  anchor="$3"
  lines="$4"
  literal="$5"
  context="$(context_before "$file" "$anchor" "$lines")"
  printf '%s\n' "$context" | grep -Fq -e "$literal" || fail "$label"
}
check_context_before_step3_launch() {
  file="$1"
  label="$2"
  lines="$3"
  literal="$4"
  context="$(context_before_step3_launch "$file" "$lines")"
  printf '%s\n' "$context" | grep -Fq -e "$literal" || fail "$label"
}

ported_verbs='step0-parse step0-session step0-route step0-clarify-hard-halt step0-init step0-abort-cleanup step0-ap-continue step0c step1d5 step1d7 step1e-reentry'
retired_paths='design-step0-parse.sh design-step0-session.sh design-step0-route.sh design-step0-clarify-hard-halt.sh design-step0-init.sh design-step0-abort-cleanup.sh design-step0-ap-continue.sh design-step0c.sh design-step1d5.sh design-step1d7.sh design-step1e-reentry.sh test-design-step0-init.sh test-design-step1d5.sh'

contains "$SKILL_MD" 'python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" design step0-session' 'Step 0 session fence must call direct Python verb'
contains "$SKILL_MD" 'NEVER use the `Monitor` tool anywhere within the `/design` orchestrator' 'Design anti-patterns must retain Monitor ban stub'
contains "$SKILL_MD" 'the sanctioned recovery path is one foreground, non-sleeping terminal-sentinel probe per recovery turn' 'Design anti-patterns must retain foreground-probe primary guidance'
contains "$SKILL_MD" 'NEVER launch a background recovery waiter' 'Design anti-patterns must retain background recovery waiter ban'
contains "$SKILL_MD" 'Do NOT fall back to Monitor' 'Design anti-patterns must retain Monitor fallback ban'
contains "$SKILL_MD" 'read `${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md` for detailed mechanics' 'Design anti-patterns must point detailed recovery to design-background-wait'
contains "$SHARED_DESIGN_WAIT_MD" 'Step 3-specific recovery note: the completion condition MUST be `[ -f "$DESIGN_TMPDIR/.completed/step-3-terminal" ]`; it MUST NOT be `.step3-review-result.env`.' 'Shared design wait must own Step 3 completion-condition literal'
contains "$SHARED_DESIGN_WAIT_MD" 'Foreground terminal-sentinel probe: after a premature notification with non-empty task output' 'Shared design wait must own foreground-probe literal'
contains "$SHARED_DESIGN_WAIT_MD" 'Foreground probes are non-sleeping `[ -f … ]` or `test -f …` checks only.' 'Shared design wait must document foreground probe forms'
contains "$SHARED_DESIGN_WAIT_MD" 'prefix the probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment' 'Shared design wait must own DESIGN_TMPDIR prefix literal'
contains "$SHARED_DESIGN_WAIT_MD" 'prefix the foreground probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment' 'Shared design wait must own foreground DESIGN_TMPDIR prefix literal'
contains "$SHARED_DESIGN_WAIT_MD" 'the backgrounded `/design` task reliably re-fires a `<task-notification>` on completion' 'Shared design wait must document notification-refire platform assumption'
not_contains "$SKILL_MD" 'WRONG — background sleep-loop recovery waiter' 'Design anti-patterns must not retain wrong/correct probe fence'
not_contains "$SKILL_MD" 'prefix the foreground probe with a single `DESIGN_TMPDIR=<absolute-path>;` assignment' 'Design anti-patterns must not retain DESIGN_TMPDIR prefix prose'
not_contains "$SKILL_MD" 'the review task reliably re-fires a `<task-notification>` on completion' 'Design anti-patterns must not retain notification-refire assumption'
not_contains "$SKILL_MD" 'When present, proceed to post-notification parsing; do not wait for a second `<task-notification>`.' 'Design anti-patterns must not retain long WAIT block'
not_contains "$ORCH_NEVER_MD" 'Load once per session' 'Shared orchestrator never must not claim session-start loading'
not_contains "$IMPL_MD" 'See `skills/implement/references/step2-dispatch.md` orchestrator wait contract and `skills/shared/orchestrator-never.md`.' 'Implement anti-patterns must not retain routine orchestrator-never wait pointer'
not_contains "$ORCH_NEVER_MD" 'only after an empty `<task-notification>`' 'Shared orchestrator never must remove empty-notification-only qualifier'
not_contains "$ORCH_NEVER_MD" 'only after the empty `<task-notification>`' 'Shared orchestrator never must remove the-empty-notification-only qualifier'
contains "$ORCH_NEVER_MD" 'For `/design`, when a premature `<task-notification>` fires with non-empty task output' 'Shared orchestrator never must document /design non-empty premature recovery'
contains "$ORCH_NEVER_MD" 'when task output is empty, end the turn without probing (#5240)' 'Shared orchestrator never must document /design empty-output no-probe recovery'
contains "$ORCH_NEVER_MD" 'For `/implement` Steps 3 and 5, premature notifications remain notification-only' 'Shared orchestrator never must document /implement Steps 3 and 5 notification-only recovery'
contains "$ORCH_NEVER_MD" 'For `/implement` Step 8, run one foreground non-sleeping `test -f "$IMPLEMENT_TMPDIR/.step-8-ship-handoff.rc"` at notification time' 'Shared orchestrator never must document /implement Step 8 rc-probe recovery'
contains "$ORCH_NEVER_MD" 'hook-allowed only while `implement-step8-ship` is live and clamped when rc stays absent' 'Shared orchestrator never must document Step 8 hook clamp'

check_context "$SKILL_MD" \
  '/design Verbosity Control uses the Step 3 post-notification load contract' \
  '**Post-notification for Step 3 waits**' \
  "8" \
  "$LOAD_LITERAL Step 3 post-notification sequence"
check_context "$SKILL_MD" \
  '/design Final summary block uses the immediate-background load contract' \
  '**When**: after `DESIGN_TMPDIR` exists' \
  "25" \
  "$LOAD_LITERAL Immediate-background wait rule"
check_context "$SKILL_MD" \
  '/design Final summary block pins durable completion confirmation purpose' \
  '**When**: after `DESIGN_TMPDIR` exists' \
  "25" \
  "$CONFIRMATION_DURABLE_COMPLETION"
check_context "$SKILL_MD" \
  '/design Final summary block pins WAIT-when-absent recovery' \
  '**When**: after `DESIGN_TMPDIR` exists' \
  "25" \
  "$WAIT_WHEN_ABSENT"
check_context_before "$SKILL_MD" \
  '/design Final summary load contract precedes its background fence' \
  "$FINAL_SUMMARY_FENCE_ANCHOR" \
  "20" \
  "$LOAD_LITERAL Immediate-background wait rule"
check_context_before_step3_launch "$SKILL_MD" \
  '/design Step 3 launch load contract precedes its background fence' \
  "20" \
  "$LOAD_LITERAL Step 3 task notification boundary"
check_context_before "$SKILL_MD" \
  '/design Step 5c load contract precedes its background fence' \
  "$STEP5C_ANCHOR" \
  "20" \
  "$LOAD_LITERAL Immediate-background wait rule"
check_context_before_step3_launch "$SKILL_MD" \
  '/design Step 3 launch loads the task notification boundary' \
  "20" \
  "$LOAD_LITERAL Step 3 task notification boundary"
check_context_before_step3_launch "$SKILL_MD" \
  '/design Step 3 launch loads the immediate-background rule' \
  "20" \
  "$LOAD_LITERAL Immediate-background wait rule"
check_context_before_step3_launch "$SKILL_MD" \
  '/design Step 3 launch loads the post-notification sequence' \
  "20" \
  "$LOAD_LITERAL Step 3 post-notification sequence"
check_context_before "$SKILL_MD" \
  '/design Step 5c uses the immediate-background load contract' \
  "$STEP5C_ANCHOR" \
  "18" \
  "$LOAD_LITERAL Immediate-background wait rule"
check_context_before "$SKILL_MD" \
  '/design Step 5c pins completion confirmation purpose' \
  "$STEP5C_ANCHOR" \
  "18" \
  "$CONFIRMATION_COMPLETION"
check_context_before "$SKILL_MD" \
  '/design Step 3 resume back-reference precedes its background fence' \
  "$STEP3_RESUME_ANCHOR" \
  "20" \
  "$RESUME_BACKREF_LITERAL"

contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step0-route --issue-number "${ISSUE_NUMBER:-}"' 'Step 0 route fence must use bare launcher verb'
contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step1d5 --mode entry' 'Step 1d.5 entry must use bare launcher verb'
contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" step1e-reentry' 'Step 1e reentry must use bare launcher verb'
contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-clarify.sh --phase fetch --issue "$ISSUE_NUMBER"' 'Clarify must stay on .sh launcher branch'
contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step2b-drafter.sh' 'Step 2b drafter must stay on .sh launcher branch'

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
contains "$DESIGN_LIFECYCLE" 'check_pause_and_exit(env=env, design_tmpdir=design_tmpdir)' 'Folded route init must retain pre-init pause check'
contains "$DESIGN_LIFECYCLE" '_run_step0_init_driver(' 'Folded route init must use the shared init driver'
contains "$DESIGN_LIFECYCLE" '_emit_step0_route_rows(route=ctx.route, resume_step=ctx.resume_step, route_env=ctx.route_env, env=ctx.env)' 'Proceed route stdout must be deferred until after init success'
contains "$DESIGN_LIFECYCLE" 'STEP1D5_ACTION=' 'Step 1d.5 entry must emit action directive'
contains "$DESIGN_LIFECYCLE" 'STEP1D5_SKIP_KIND=' 'Step 1d.5 entry must emit skip-kind directive'
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
contains "$SKILL_MD" 'If the fence output contains a whole-line `PAUSE_OK=true` row, treat Step 0b as a terminal pause-save boundary.' 'Step 0 route must stop on PAUSE_OK before route continuation parsing'
contains "$SKILL_MD" 'Dominant proceed-path guard: when `ROUTE=proceed` and the `step0-route` fence stdout contains whole-line `INIT_STATUS=ok` and `RUN_PARAMS_PATH=`, skip Sub-step 6 entirely.' 'Sub-step 6 must skip when folded route init completed'
contains "$SKILL_MD" 'Do not rewrite `feature-description.txt`, do not invoke `design init-runparams`, and do not run `step0-init`; folded init inside `step0-route` already produced those artifacts.' 'Sub-step 6 must not run step0-init on dominant proceed path'
contains "$SKILL_MD" 'Before running the entry fence, read `$DESIGN_TMPDIR/run-params.json` and apply `_step1d5_brainstorm_requested` semantics: only `brainstorm_requested: true` in a well-formed object means brainstorm-on; missing, malformed, symlinked, or non-`true` values mean brainstorm-off.' 'Step 1d.5 must document run-params authority before entry fence elision'
contains "$SKILL_MD" 'This run-params authority overrides mental Step 0-pre `brainstorm_requested` on `resume@*` paths where Sub-step 5 flag binding was skipped.' 'Step 1d.5 elision must not trust stale mental brainstorm binding'
contains "$SKILL_MD" 'If the entry fence output contains a whole-line `PAUSE_OK=true` row, treat Step 1d.5 as a terminal pause-save boundary.' 'Step 1d.5 must stop on PAUSE_OK before action parsing'
contains "$SKILL_MD" 'If `STEP1D5_ACTION` is missing or empty, print `**⚠ 1d.5: missing STEP1D5_ACTION from entry fence; aborting /design**` and abort `/design`' 'Step 1d.5 must fail closed on missing action'
contains "$SKILL_MD" 'If `STEP1D5_ACTION=skip`:' 'Step 1d.5 must branch on skip directive'
contains "$SKILL_MD" 'If `STEP1D5_SKIP_KIND=already-complete`: print `⏩ 1d.5: brainstorm — skipped (already complete; .brainstorm-done present)`.' 'Step 1d.5 must preserve already-complete breadcrumb'
contains "$SKILL_MD" 'If `STEP1D5_ACTION=run`: **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/brainstorm.md` completely.' 'Step 1d.5 must branch on run directive'
contains "$SKILL_MD" 'If the fence output contains a whole-line `PAUSE_OK=true` row, treat Step 1d.7 as a terminal pause-save boundary. Stop `/design` for operator resume; do not parse `SKIP_APPROVE_REQUESTED`; do not read or execute `references/design-outline.md`.' 'Step 1d.7 must stop on PAUSE_OK before skip-approve and outline work'
contains "$SKILL_MD" 'If the fence output contains a whole-line `PAUSE_OK=false` row or `SKIP_APPROVE_REQUESTED` is missing or empty, print `**⚠ 1d.7: missing SKIP_APPROVE_REQUESTED from step1d7 fence; aborting /design**` and abort `/design`' 'Step 1d.7 must fail closed on pause failure or missing skip-approve directive'
not_contains "$SKILL_MD" 'Run exactly once after skip or finish' 'Step 1d.5 must not describe completion fence as after skip'

contains "$MAKEFILE" 'python3 -m pytest python/tests/design/test_design_lifecycle.py' 'Make targets must route retired shell harnesses to pytest'

g6_terminal_retired_paths='design-stage-terminal-state.sh design-stage-terminal-state.md test-design-stage-terminal-state.sh test-design-stage-terminal-state.md design-failure-report.sh design-failure-report.md test-design-failure-report.sh test-design-failure-report.md design-step-final-summary.sh design-step-final-summary.md _dbg-stage.sh _debug-step5c.sh'
for retired in $g6_terminal_retired_paths; do
  [ ! -e "$ROOT/skills/design/scripts/$retired" ] || fail "retired G6.2 script still exists: $retired"
  contains "$MIGRATED" "skills/design/scripts/$retired" "migrated-scripts.tsv missing $retired"
done
debug_step5c_once='debug-step5c-once.sh'
[ ! -e "$ROOT/scripts/$debug_step5c_once" ] || fail "retired G6.2 script still exists: scripts/$debug_step5c_once"
contains "$MIGRATED" "scripts/$debug_step5c_once" "migrated-scripts.tsv missing scripts/$debug_step5c_once"

step2_verbs='step2b-drafter step2b-postplan step2b5'
step2_retired_paths='design-step2a.sh design-step2a.md design-step2b-drafter.sh design-step2b-drafter.md design-step2b-postplan.sh design-step2b-postplan.md design-step2b5.sh design-step2b5.md design-step-validator-autofix.sh design-step-validator-autofix.md design-step2b-prelude.sh design-step2b-prelude.md test-design-step2b-drafter.sh test-design-step2b-drafter.md test-design-step-validator-autofix.sh test-design-step-validator-autofix.md'
SETTLE_SH="$ROOT/skills/design/scripts/design-step35-settle.sh"
SETTLE_MD="$ROOT/skills/design/scripts/design-step35-settle.md"
DESIGN_POSTPLAN="$ROOT/python/larch/design/design_postplan.py"

for verb in $step2_verbs; do
  contains "$CLI_PY" "(\"design\", \"$verb\")" "cli registry missing design $verb"
  printf '%s' "$stdout_keys_block" | grep -Fq "(\"design\", \"$verb\")" || fail "cli _DESIGN_LIFECYCLE_STDOUT_KEYS missing design $verb"
done
contains "$CLI_PY" '("plan", "validator-autofix")' 'cli registry missing plan validator-autofix'

for retired in $step2_retired_paths; do
  [ ! -e "$ROOT/skills/design/scripts/$retired" ] || fail "retired Step 2 script still exists: $retired"
  contains "$MIGRATED" "skills/design/scripts/$retired" "migrated-scripts.tsv missing $retired"
done

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
contains "$DESIGN_LIFECYCLE" 'DRAFTER_NEXT_ACTION=' 'Step 2 drafter must emit trusted DRAFTER_NEXT_ACTION rows'
not_contains "$DESIGN_LIFECYCLE" 'DRAFTER_STATUS=succeeded' 'Step 2 drafter must not retain retired DRAFTER_STATUS=succeeded row'
not_contains "$DESIGN_LIFECYCLE" 'DRAFTER_STATUS=fallback' 'Step 2 drafter must not retain retired DRAFTER_STATUS=fallback row'
not_contains "$DESIGN_LIFECYCLE" 'DRAFTER_STATUS=dirty-tree' 'Step 2 drafter must not retain retired DRAFTER_STATUS=dirty-tree row'
contains "$DESIGN_LIFECYCLE" 'snapshot_original=True' 'Step 2 drafter must delegate postplan with snapshot-original'
contains "$DESIGN_LIFECYCLE" '_valid_step2b_sentinels' 'Step 2 drafter must validate Step 2a sentinels in-process'
contains "$DESIGN_LIFECYCLE" '_folded_step2a_sentinel_prep(design_tmpdir)' 'Step 2 drafter must repair-or-refuse folded Step 2a sentinels in-process'
contains "$DESIGN_LIFECYCLE" '.drafter-next-action-rc12.txt' 'Step 2 drafter must clear/write rc12 action sidecar'
contains "$DESIGN_LIFECYCLE" '.drafter-next-action-rc13.txt' 'Step 2 drafter must clear/write rc13 action sidecar'
contains "$DESIGN_LIFECYCLE" 'defer_pause_save=True' 'Step 2 drafter must defer shared postplan pause-save to caller'
contains "$DESIGN_LIFECYCLE" 'if result.postplan_rc == 11:' 'terminal Step 2b postplan must own rc11 pause-save branch'
shared_postplan_body="$(awk 'index($0, "def _shared_step2b_postplan_body(") == 1 {flag=1} index($0, "def step2b_postplan_main(") == 1 {flag=0} flag' "$DESIGN_LIFECYCLE")"
printf '%s' "$shared_postplan_body" | grep -Fq 'return PostplanResult(11, "POSTPLAN_RC=11\nPOSTPLAN_STATUS=pause-save\n", "pause-save")' || fail "shared postplan body must return rc11 rows without printing"
printf '%s' "$shared_postplan_body" | grep -Fq 'print("POSTPLAN_RC=11")' && fail "shared postplan body must not print POSTPLAN_RC=11 directly"
printf '%s' "$shared_postplan_body" | grep -Fq 'print("POSTPLAN_STATUS=pause-save")' && fail "shared postplan body must not print POSTPLAN_STATUS=pause-save directly"
contains "$SKILL_MD" 'On exit 0 only, parse the final trusted `DRAFTER_NEXT_ACTION=` row after the final whole-line `STEP2B_DRAFTER_WRAPPER_ROWS_BEGIN=1` delimiter.' 'SKILL.md must route Step 2b through DRAFTER_NEXT_ACTION'
contains "$SKILL_MD" 'If the `design-step2b-drafter.sh` fence exits non-zero, abort loudly with captured stdout/stderr and do not parse `DRAFTER_NEXT_ACTION`, enter inline fallback, run fail-safe, or continue to Step 3.' 'SKILL.md must abort on non-zero drafter fence before parsing action'
contains "$SKILL_MD" '`failsafe-missing-rows` — load `references/step2b-drafter-failsafe.md` and run the retained terminal postplan path only; this token is valid only after exit 0 without a trusted postplan action row.' 'SKILL.md must scope failsafe-missing-rows to zero exit only'
contains "$SKILL_MD" 'Do not reconstruct drafter routing from `POSTPLAN_RC`, `POSTPLAN_STATUS`, `DRAFTER_STATUS`, `PAUSE_OK`, preview text, or `.step2b-postplan-inline-retry-pending`.' 'SKILL.md must not parse drafter outcomes from retired rows'
contains "$SKILL_MD" 'Do not describe or perform a `fallback_used` disk re-read after postplan apply.' 'SKILL.md inline retry must not re-read fallback_used after apply'
contains "$SKILL_MD" 'When `ROUTE=resume@2a` or `RESUME_STEP=2a`, jump directly to the Step 2b drafter breadcrumb (`> **🔶 /design 2b: full plan**`) and `design-step2b-drafter.sh`; folded sentinel prep runs inside that wrapper, so do not expect or invoke a standalone Step 2a fence.' 'SKILL.md resume@2a must route directly to Step 2b drafter'
contains "$DESIGN_POSTPLAN" 'DRIFT_TRIGGER_FIRED' 'design_postplan must parse drift trigger'
contains "$DESIGN_POSTPLAN" 'BASELINE_PLAN_LINES' 'design_postplan must parse drift baseline'

assert_step3b_classifier false $'## Files to modify/create\n### MAY_UPDATE: docs/issue-anchored-plan.md' 'MAY_UPDATE docs path must not require diagram'
assert_step3b_classifier false $'## Files to modify/create\n### MAY_UPDATE: `docs/issue-anchored-plan.md`' 'MAY_UPDATE backtick docs path must not require diagram'
assert_step3b_classifier true $'## Files to modify/create\n### MAY_UPDATE: skills/design/scripts/foo.sh' 'MAY_UPDATE script path must require diagram'

contains "$SKILL_MD" '${CLAUDE_PLUGIN_ROOT}/skills/shared/subskill-invocation.md#anti-halt' 'design anti-halt must cite shared anti-halt anchor'
contains "$SKILL_MD" 'after every visible output (plans, voting tallies, skip breadcrumbs), IMMEDIATELY continue' 'design anti-halt must retain visible-output continuation trigger'
contains "$SKILL_MD" 'After Step 5c `python/cli.py design step5c` returns with `_publish_rc` 0, 1, or 3, or after any cancellation outcome'\''s Final summary block has written a non-empty summary file' 'design anti-halt must retain operative no-recap trigger'
contains "$SKILL_MD" 'NEVER write a free-form natural-language recap summary: no "Design complete." line, no artifact bullet list, no parenthetical cost paraphrase such as `~$10.46`' 'design anti-halt must retain no-recap and no-cost paraphrase ban'
contains "$SKILL_MD" '**Not** gated on `python/cli.py design render-final-summary` exit 0' 'design anti-halt must retain render-exit carve-out'
contains "$SKILL_MD" 'No free-form recap may appear between or after those pieces.' 'Step 5d must retain no-recap ordering token'
contains "$SKILL_MD" 'design-step-final-summary.sh' 'design final-summary cancellation source must remain named'
contains "$SKILL_MD" 'design-step5c.sh' 'design Step 5c final-summary source must remain named'
contains "$SKILL_MD" 'follow the file-only profile in `${CLAUDE_PLUGIN_ROOT}/skills/shared/final-summary-emit.md`' 'design file-only cancellation profile must remain named'
not_contains "$SKILL_MD" 'Binding: markers `LARCH_FINAL_SUMMARY_BEGIN` / `LARCH_FINAL_SUMMARY_END`' 'design SKILL must not retain marker-body Binding restatement'
contains "$SKILL_MD" '1c→1d→1d.5→1d.7→2a(folded)→2b→2b.5→3→3.5→3b→4→4b→5→5b→5b.5→5c.1→5c.5→5c.7→5c.8→6' 'anti-halt chain must include Step 5b.5 before Step 5c'
contains "$SKILL_MD" 'design-step3b-entry.sh --mode finalize' 'Step 3b must use finalize mode'
contains "$SKILL_MD" 'design-step3b-entry.sh --mode diagram' 'Step 5b.5 must use diagram mode'
contains "$SKILL_MD" 'STEP3_REENTRY_FLAG=""' 'Step 3 entry must document first-time empty reentry flag'
contains "$SKILL_MD" 'STEP3_REENTRY_FLAG="--reentry"' 'Step 3 entry must document caller-owned reentry flag'
contains "$SKILL_MD" 'design-step3-entry.sh ${STEP3_REENTRY_FLAG}' 'Step 3 entry must use one parameterized launcher fence'
not_contains "$SKILL_MD" '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-entry.sh --reentry' 'SKILL must not retain standalone Step 3 reentry launcher fence'
_step3_entry_launcher_count=$(grep -Fc '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-entry.sh' "$SKILL_MD" || true)
[ "$_step3_entry_launcher_count" -eq 1 ] || fail "SKILL must retain exactly one Step 3 entry launcher fence, found $_step3_entry_launcher_count"
contains "$SKILL_MD" 'Before launching external reviewers, verify the implementation plan exists at `$DESIGN_TMPDIR/plan.txt`' 'External reviewer setup must retain prompt-side plan.txt check'
contains "$SKILL_MD" 'Reviewer focus areas are delegated to `plan-review.md` and the rendered reviewer prompts.' 'External reviewer setup must delegate focus areas'
not_contains "$SKILL_MD" '_step4_debate_may_run' 'Step 4 must not self-compute debate may-run flag'
not_contains "$SKILL_MD" 'dialectic-gatec --design-tmpdir "$DESIGN_TMPDIR" --probe-only' 'Step 4 must not run prompt-side dialectic probe'
contains "$SKILL_MD" 'Step 4 routing authority is `STEP4_MODE` only.' 'Step 4 must route only on STEP4_MODE'
contains "$SKILL_MD" 'bind `STEP4_MODE` from a whole-line `STEP4_MODE=foreground|background` row in the finalize wrapper stdout' 'Step 4 must bind STEP4_MODE from finalize stdout'
contains "$SKILL_MD" 'read `$DESIGN_TMPDIR/.step4-mode.env` and bind the same grammar from that sidecar' 'Step 4 must support STEP4_MODE sidecar fallback'
contains "$SKILL_MD" 'If `STEP4_MODE=foreground`, run the tail in the foreground' 'Step 4 must document foreground tail route'
contains "$SKILL_MD" 'If `STEP4_MODE=background`, **MANDATORY — READ ENTIRE FILE**: read and apply `${CLAUDE_PLUGIN_ROOT}/skills/shared/design-background-wait.md`' 'Step 4 must document background wait read'
contains "$SKILL_MD" 'Stop for repair if `STEP4_MODE` is absent or not `foreground|background`.' 'Step 4 must fail closed on invalid STEP4_MODE'
not_contains "$SKILL_MD" '**Optional trailer guard (Gate B post-apply)**' 'SKILL must not retain inline Gate B optional trailer block'
not_contains "$SKILL_MD" 'Before any reviewer-finding `plan.txt` replacement, run' 'SKILL must not retain inline Gate B snapshot-trailers restatement'
not_contains "$SKILL_MD" '**Gate B resume idempotency**' 'SKILL must not retain inline Gate B resume idempotency block'
not_contains "$SKILL_MD" 'do not probe the apply-ready marker' 'SKILL must not retain old Gate B idempotency probe wording'
contains "$SKILL_MD" 'Apply the `approval-gates.md` §Gate B **Resume idempotency guard** before executing Gate B.' 'SKILL must point Gate B idempotency to approval-gates'
contains "$SKILL_MD" 'runs FINALIZE, runs probe-only dialectic eligibility, emits and persists `STEP4_MODE`, then writes `.completed/step-3b`' 'Step 3b prose must document finalize ordering'
contains "$SKILL_MD" 'before executing hard / partition / drift / no-trigger branches 4–7 for `SETTLE_NEXT_ACTION=gate-a-hard-size`' 'Step 2b.5 direct-entry must be action-row only'
not_contains "$SKILL_MD" 'Gate A / discussion-round2 fallback rc `12`' 'Step 2b.5 direct-entry must not mention Gate A fallback rc 12'
not_contains "$SKILL_MD" 'Gate B fallback rc `12`' 'Step 2b.5 direct-entry must not mention Gate B fallback rc 12'
contains "$SKILL_MD" 'When `LOOP_STATUS=cap-reached` or `TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached`, do not enter Gate B because stale accepted findings from an earlier round would re-surface.' 'Gate-B-bypass row must retain cap-reached stale-findings rationale'
not_contains "$SKILL_MD" 'If `NEXT_ACTION=step3b-bypass` with `LOOP_STATUS=cap-reached`' 'SKILL must not retain standalone cap-reached bypass paragraph'
not_contains "$SKILL_MD" 'If `NEXT_ACTION=step3b-bypass` with `LOOP_STATUS=tally-error`' 'SKILL must not retain standalone degraded bypass paragraph'
not_contains "$SKILL_MD" 'Before every Gate-B-bypass jump, run `design-step3-gate-b-bypass.sh` so pause/resume lands at Step 3b' 'SKILL must not retain duplicated Gate-B-bypass restatement'
not_contains "$SKILL_MD" 'Before every Gate-B-bypass jump to Step 3b, run:' 'SKILL must not retain duplicated Gate-B-bypass launcher header'
_gate_b_bypass_launcher_count=$(grep -Fc '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step3-gate-b-bypass.sh' "$SKILL_MD" || true)
[ "$_gate_b_bypass_launcher_count" -eq 0 ] || fail "SKILL Gate-B-bypass routing row owns contract; must not retain inline launcher fence, found $_gate_b_bypass_launcher_count"
contains "$STEP3B_ENTRY" '.completed/step-4' 'diagram mode must require step-4 sentinel'
contains "$STEP3B_ENTRY" '.completed/step-5b' 'diagram mode must require step-5b sentinel'
contains "$STEP3B_ENTRY" '--probe-only' 'finalize mode must call dialectic-gatec probe-only internally'
contains "$STEP3B_ENTRY" '>"$_probe_stdout" 2>"$_probe_stderr"' 'finalize mode must capture probe stdout/stderr internally'
contains "$STEP3B_ENTRY" 'STEP4_MODE=%s' 'finalize mode must expose STEP4_MODE on success'
contains "$STEP3B_ENTRY" '.step4-mode.env' 'finalize mode must persist STEP4_MODE sidecar'
contains "$STEP3B_ENTRY" 'true) _step4_mode=background' 'finalize mode must map debate required to background'
contains "$STEP3B_ENTRY" 'false) _step4_mode=foreground' 'finalize mode must map no debate to foreground'
# shellcheck disable=SC1003 # \\ is a gawk-safe literal-backslash needle for assert_line_precedes awk -v
assert_line_precedes "$STEP3B_ENTRY" '    --probe-only \\' '  : > "$DESIGN_TMPDIR/.completed/step-3b"' 'finalize probe must precede step-3b marker write'
_run_finalize_body="$(awk '/^run_step3b_finalize\(\) \{/{flag=1} flag{print} flag && /^}/{exit}' "$STEP3B_ENTRY")"
if printf '%s\n' "$_run_finalize_body" | grep -Fq '.completed/step-3b'; then
  fail 'run_step3b_finalize must not write step-3b marker'
fi
not_contains "$STEP3B_ENTRY" '.completed/dialectic-gatec-terminal' 'finalize entry wrapper must not write dialectic terminal sentinel'
contains "$STEP3B_ENTRY_MD" 'Finalize-mode stdout exposes exactly one whole-line `STEP4_MODE=foreground|background` on success.' 'step3b entry docs must document STEP4_MODE stdout contract'
contains "$STEP3B_ENTRY_MD" '$DESIGN_TMPDIR/.step4-mode.env' 'step3b entry docs must document STEP4_MODE sidecar'
contains "$STEP3B_ENTRY_MD" '`run_step3b_finalize` no longer writes `.completed/step-3b`' 'step3b entry docs must document helper marker removal'
contains "$STEP3B_ENTRY_MD" 'Driver success alone does not complete Step 3b.' 'step3b entry docs must document driver success boundary'
contains "$STEP3B_ENTRY_MD" 'Finalize mode does not run the Gate C debate and does not write `.completed/dialectic-gatec-terminal`.' 'step3b entry docs must document no Gate C debate in finalize'
[ -f "$FINALIZE_STEP5_MD" ] || fail "finalize-step5 reference missing"
grep -Eq '^\*\*Consumer\*\*:' "$FINALIZE_STEP5_MD" || fail "finalize-step5 must anchor Consumer header"
grep -Eq '^\*\*Contract\*\*:' "$FINALIZE_STEP5_MD" || fail "finalize-step5 must anchor Contract header"
grep -Eq '^\*\*When to load\*\*:' "$FINALIZE_STEP5_MD" || fail "finalize-step5 must anchor When to load header"
assert_followed_count_at_least "$SKILL_MD" \
  '**Invariant (anti-pattern):** do **not** reorder finalize sub-steps to run the `[DESIGNED]` rename (old Step 5c tail) before OOS filing (Step 5b) completes successfully — that would publish a terminal title while accepted OOS items are not yet filed. Step **5b** MUST run before Step **5b.5**, and Step **5c** MUST complete the Step **5b.5** sanitize gate before `larch:plan` write, publish, and rename.' \
  '**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/finalize-step5.md` completely.' \
  1 'SKILL Step 5 must load finalize-step5 immediately after invariant'
assert_line_precedes "$SKILL_MD" \
  '**MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/finalize-step5.md` completely.' \
  '"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step5b-prepare.sh' \
  'SKILL Step 5 must load finalize-step5 before prepare fence'
contains "$FINALIZE_STEP5_MD" 'Append only a bounded warning to `execution-issues.md` via `design_diagram_log.write_bounded_diagram_failure_log`' 'Step 5b.5 generation failure must use bounded warning logging'
not_contains "$SKILL_MD" 'design_diagram_log.write_bounded_diagram_failure_log' 'SKILL must not retain diagram warning logging body'
contains "$FINALIZE_STEP5_MD" 'Step 5b.5 diagram generation paths append bounded warnings only. Step 5c sanitizes the candidate before publish.' 'Step 5c must own diagram sanitize before publish'
contains "$SKILL_MD" 'architecture diagram content is issue-only via `larch:diagrams`' 'SKILL verbosity must not authorize architecture diagram chat emission'
contains "$SKILL_MD" 'Continue to Step 5b.5 IMMEDIATELY' 'Step 5b must continue to Step 5b.5 before Step 5c'
contains "$FINALIZE_STEP5_MD" 'read `skills/design/references/readability-style.md` once at Step 5 entry before diagram or final plan prose composition' 'finalize-step5 must require one Step 5 readability load'
_readability_step5_count=$(grep -Fc 'readability-style.md' "$FINALIZE_STEP5_MD" || true)
[ "$_readability_step5_count" -eq 1 ] || fail "finalize-step5 must reference readability-style.md once, found $_readability_step5_count"
not_contains "$SKILL_MD" 'readability-style.md`.**' 'SKILL must not retain inline orchestrator readability anchors after move'
contains "$SKILL_MD" 'Parse `NEXT_ACTION=` from `$DESIGN_TMPDIR/oos-filing-prepare.env`' 'Step 5b prose must branch on NEXT_ACTION'
contains "$SKILL_MD" '`unknown-oos-status`' 'Step 5b must special-case unknown-oos-status on non-zero prepare rc'
contains "$SKILL_MD" 'stop for repair' 'Step 5b must stop for repair on unknown OOS status'
contains "$OOS_STEP5B_DISPATCH_MD" 'unknown-oos-status' 'oos step5b dispatch must document unknown-oos-status repair stop'
contains "$FINALIZE_STEP5_MD" 'call `design-step5b-annotate.sh` only when `$DESIGN_TMPDIR/oos-issue.stdout.txt` exists and is non-empty' 'skip-already-filed must retain stdout-non-empty annotate guard'
not_contains "$SKILL_MD" 'call `design-step5b-annotate.sh` only when' 'SKILL must not retain skip-already annotate guard body'
contains "$FINALIZE_STEP5_MD" 'tool `python/cli.py design file-oos-prepare`, category `Warnings`, exit code 0' 'skip-already-filed must append WARN rows as warnings'
not_contains "$SKILL_MD" 'tool `python/cli.py design file-oos-prepare`, category `Warnings`, exit code 0' 'SKILL must not retain skip-already WARN body'
contains "$FINALIZE_STEP5_MD" 'Prepare already wrote `.completed/step-5b` for `skip-already-filed-sentinel` without annotate.' 'skip-already-filed without annotate must rely on prepare completion marker'
not_contains "$SKILL_MD" 'skip-already-filed-sentinel` without annotate.' 'SKILL must not retain skip-already completion body'
not_contains "$SKILL_MD" 'skills/design/references/oos-step5b-dispatch.md' 'Step 5b must not mandatory-read oos-step5b dispatch fallback'
contains "$SKILL_MD" 'When `NEXT_ACTION` is missing, unknown, or `unknown-oos-status`, stop for repair. The prepare wrapper already checks `FILE_DESIGN_OOS_STATUS=` agreement.' 'Step 5b must fail closed without prompt-side fallback derivation'
[ -f "$DIALECTIC_LEGACY_ATTIC_MD" ] || fail "dialectic legacy attic doc missing"
[ ! -e "$ROOT/skills/design/references/dialectic-legacy.md" ] || fail "retired dialectic-legacy runtime reference still exists"
[ -f "$OOS_STEP5B_DISPATCH_MD" ] || fail "oos step5b dispatch reference missing"
grep -Eq '^\*\*When to load\*\*:' "$OOS_STEP5B_DISPATCH_MD" || fail "oos step5b dispatch must anchor When to load header"
contains "$OOS_STEP5B_DISPATCH_MD" 'Current `python/cli.py design step5b-prepare` must emit a whole-line `NEXT_ACTION=...` row in `oos-filing-prepare.env`.' 'oos step5b dispatch must name current NEXT_ACTION contract'
contains "$OOS_STEP5B_DISPATCH_MD" 'Do not derive a prompt-side route from `FILE_DESIGN_OOS_STATUS`.' 'oos step5b dispatch must reject prompt-side fallback derivation'
contains "$OOS_STEP5B_DISPATCH_MD" 'The historical mapping was: `ready` to `file-issues`; `skip-sentinel`, `skip-already-filed-sentinel`, `skip-no-items`, and `skip-all-security` to `skip-pipeline`; every other status to `unknown-oos-status`.' 'oos step5b dispatch must keep short legacy mapping note'
not_contains "$OOS_STEP5B_DISPATCH_MD" '## Fallback: branch on FILE_DESIGN_OOS_STATUS' 'oos step5b dispatch must not own a live fallback table'
contains "$FINALIZE_STEP5_MD" 'STEP5B_STATUS=prepare-failed-continue' 'finalize-step5 must own prepare-failed-continue branch'
not_contains "$SKILL_MD" 'STEP5B_STATUS=prepare-failed-continue' 'SKILL must not retain prepare-failed-continue body'
contains "$FINALIZE_STEP5_MD" 'FILE_DESIGN_OOS_DEPS_AVAILABLE=true' 'finalize-step5 must own file-issues deps detail'
not_contains "$SKILL_MD" 'FILE_DESIGN_OOS_DEPS_AVAILABLE=true' 'SKILL must not retain file-issues deps body'
contains "$FINALIZE_STEP5_MD" 'Manual OOS recovery when annotate ran before' 'finalize-step5 must own manual OOS recovery'
not_contains "$SKILL_MD" 'Manual OOS recovery when annotate ran before' 'SKILL must not retain manual OOS recovery'
contains "$FINALIZE_STEP5_MD" 'Compose `$DESIGN_TMPDIR/composed-plan.md`' 'finalize-step5 must own Step 5c composition detail'
not_contains "$SKILL_MD" 'Compose `$DESIGN_TMPDIR/composed-plan.md`' 'SKILL must not retain Step 5c composition detail'
contains "$FINALIZE_STEP5_MD" 'Driver WARN replay (top chat)' 'finalize-step5 must own driver WARN replay detail'
contains "$SKILL_MD" 'Follow `finalize-step5.md` for `_publish_rc` abort handling, stdout fallback, validator-defect routing, and `PLAN_WRITE_OK` branches.' 'SKILL must point rare publish rc handling to finalize-step5'
contains "$FINALIZE_STEP5_MD" 'When `_publish_rc=2` or an unexpected non-zero value outside `{0,1,3,4}` appears, abort after best-effort `python/cli.py design stage-terminal-state` staging as `failed-publish-tail`.' 'finalize-step5 must own rc2 and unexpected non-zero abort guidance'
contains "$FINALIZE_STEP5_MD" 'This includes `_publish_rc=5`.' 'finalize-step5 must own rc5 abort guidance'
contains "$FINALIZE_STEP5_MD" 'When `_publish_rc=3`, the publish tail may have completed but `.design-publish-result.env` could not be written.' 'finalize-step5 must own rc3 stdout fallback guidance'
not_contains "$SKILL_MD" '_publish_rc`=2 and unexpected non-zero values outside `{0,1,3,4}`' 'SKILL must not retain publish rc abort wall'
contains "$FINALIZE_STEP5_MD" 'Step 5d warning replay and footer' 'finalize-step5 must own Step 5d warning replay detail'
contains "$SKILL_MD" 'architecture diagram work runs only at Step 5b.5 after Gate C approval' 'Step 2b anti-halt must not promise pre-approval diagram generation'
not_contains "$SKILL_MD" 'design-run-$PPID.sh" design-step3b-sanitize.sh' 'SKILL must not retain standalone Step 5b.5 sanitizer fence'
contains "$STEP3B_SANITIZE" 'architecture-diagram.skipped' 'sanitizer fail-closed paths must touch skipped marker'
contains "$STEP3B_SANITIZE" 'design Step 5b.5' 'sanitizer warning site must name Step 5b.5'
not_contains "$STEP3B_SANITIZE" 'LARCH-DIAGRAM' 'sanitizer must not emit chat diagram markers'
not_contains "$SKILL_MD" 're-emit that exact body verbatim in chat' 'SKILL must not instruct diagram body re-emission'

contains "$SETTLE_SH" 'python/cli.py" design step2b-postplan' 'settle must default to python/cli.py design step2b-postplan'
contains "$SETTLE_SH" '--site "$POSTPLAN_SITE"' 'settle must pass mapped postplan site'
contains "$SETTLE_SH" '"${PUBLIC_ARGV_WORDS[@]}"' 'settle must forward caller tail after --'
contains "$SETTLE_MD" 'python/cli.py design step2b-postplan --site gate-b' 'settle doc must name gate-b postplan authority'
contains "$SETTLE_MD" 'python/cli.py design step2b-postplan --site discussion-round2' 'settle doc must name discussion postplan authority'
contains "$SETTLE_MD" 'python/tests/design/test_design_lifecycle.py' 'settle doc must name pytest structure coverage'
contains "$SETTLE_MD" 'The process rc remains a wrapper diagnostic and legacy process contract.' 'settle doc must describe process rc as diagnostic only'
not_contains "$SETTLE_MD" 'compatibility fallback' 'settle doc must not call process rc a prompt fallback'

[ -f "$SETTLE_DISPATCH_MD" ] || fail "settle rc dispatch reference missing"
grep -Eq '^\*\*When to load\*\*:' "$SETTLE_DISPATCH_MD" || fail "settle rc dispatch must anchor When to load header"
contains "$SETTLE_DISPATCH_MD" 'Primary key: branch on the whole-line `SETTLE_NEXT_ACTION=...` row from `design-step35-settle.sh` stdout.' 'settle dispatch must name primary SETTLE_NEXT_ACTION key'
contains "$SETTLE_DISPATCH_MD" 'If the `SETTLE_NEXT_ACTION` action row is absent, stop for operator repair. Do not route from the wrapper rc when the action row is missing.' 'settle dispatch must fail closed when action row is absent'
contains "$SETTLE_DISPATCH_MD" 'If `SETTLE_NEXT_ACTION` and wrapper rc disagree, stop for repair rather than silently choosing one.' 'settle dispatch must stop on action rc disagreement'
contains "$SETTLE_DISPATCH_MD" 'Wrapper exit codes remain diagnostics and legacy process contracts only. The orchestrator must not use them as fallback routing authority.' 'settle dispatch must keep wrapper rc diagnostic-only'
contains "$SETTLE_DISPATCH_MD" 'There is no `POSTPLAN_RC=1` on the postplan path.' 'settle rc dispatch must reject POSTPLAN_RC=1 wording'
not_contains "$SETTLE_DISPATCH_MD" 'Fallback key: when the action row is missing' 'settle dispatch must remove fallback key paragraph'
not_contains "$SETTLE_DISPATCH_MD" '## Fallback: branch on wrapper rc' 'settle dispatch must remove wrapper rc fallback section'
not_contains "$SETTLE_DISPATCH_MD" '## Site variants for fallback rc dispatch' 'settle dispatch must remove site variant fallback section'
not_contains "$SETTLE_DISPATCH_MD" '| **Gate B** |' 'settle dispatch must remove Gate B fallback variant row'
not_contains "$SETTLE_DISPATCH_MD" '| **Gate A / discussion-round2** |' 'settle dispatch must remove Gate A fallback variant row'

for caller in "$SKILL_MD" "$APPROVAL_GATES_MD" "$DISCUSSION_ROUNDS_MD"; do
  contains "$caller" 'skills/design/references/settle-rc-dispatch.md' "caller must reference settle rc dispatch: $caller"
done
assert_followed_count_at_least "$APPROVAL_GATES_MD" '   1. **MANDATORY — READ ENTIRE FILE**: Read `skills/design/references/settle-rc-dispatch.md` completely.' '   2. Require `SETTLE_NEXT_ACTION`; stop for repair if it is absent. If the action row and wrapper rc disagree, stop for repair. Branch only on the matching `SETTLE_NEXT_ACTION` row in `settle-rc-dispatch.md`.' 1 'approval-gates must load settle dispatch immediately before Gate B branch directive'
assert_followed_count_at_least "$DISCUSSION_ROUNDS_MD" '1. **MANDATORY — READ ENTIRE FILE**: Read `skills/design/references/settle-rc-dispatch.md` completely.' '2. Require `SETTLE_NEXT_ACTION`; stop for repair if it is absent. Branch only on the matching `SETTLE_NEXT_ACTION` row in `settle-rc-dispatch.md`.' 1 'discussion-rounds must use numbered settle dispatch steps 1-2'
assert_followed_count_at_least "$SKILL_MD" '1. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/settle-rc-dispatch.md` completely (if not already loaded at discussion-round2).' '2. Require `SETTLE_NEXT_ACTION`; stop for repair if it is absent. If the action row and wrapper rc disagree, stop for repair. Branch only on the matching `SETTLE_NEXT_ACTION` row in `settle-rc-dispatch.md`.' 1 'SKILL Gate A guard must load settle dispatch immediately before branch directive'
assert_followed_count_at_least "$SKILL_MD" '1. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/settle-rc-dispatch.md` completely (if not already loaded at Step 1e).' '2. Require `SETTLE_NEXT_ACTION`; stop for repair if it is absent. If the action row and wrapper rc disagree, stop for repair. Branch only on the matching `SETTLE_NEXT_ACTION` row in `settle-rc-dispatch.md`.' 1 'SKILL Gate B guard must load settle dispatch immediately before branch directive'

not_contains "$APPROVAL_GATES_MD" 'Branch on the settle wrapper rc' 'approval-gates must not retain inline settle rc branch table'
not_contains "$APPROVAL_GATES_MD" 'Branch on wrapper rc' 'approval-gates must not retain inline wrapper rc branch table'
not_contains "$APPROVAL_GATES_MD" 'fallback row' 'approval-gates must not retain Gate B fallback-row prose'
not_contains "$DISCUSSION_ROUNDS_MD" 'Branch on the settle wrapper rc' 'discussion-rounds must not retain inline settle rc branch table'
not_contains "$DISCUSSION_ROUNDS_MD" 'Branch on wrapper rc' 'discussion-rounds must not retain inline wrapper rc branch table'
not_contains "$DISCUSSION_ROUNDS_MD" 'fallback row' 'discussion-rounds must not retain fallback-row prose'
not_contains "$SKILL_MD" 'Branch on the settle wrapper rc' 'SKILL must not retain inline settle rc branch table'
not_contains "$SKILL_MD" 'Branch on wrapper rc' 'SKILL must not retain inline wrapper rc branch table'
not_contains "$SKILL_MD" 'fallback row' 'SKILL must not retain settle fallback-row prose'

contains "$STEP2B5_RC_MD" 'settle dispatch `SETTLE_NEXT_ACTION=gate-a-hard-size`' 'step2b5 rc handling must keep gate-a-hard-size direct-entry trigger'
contains "$STEP2B5_RC_MD" 'Do not route to this reference from a wrapper rc when `SETTLE_NEXT_ACTION` is missing.' 'step2b5 rc handling must reject wrapper-rc fallback routing'
contains "$STEP2B5_RC_MD" '`SETTLE_NEXT_ACTION=gate-b-hard-size`; that action uses the existing Gate B hard plan-size prompt in `approval-gates.md`, not this reference.' 'step2b5 rc handling must delegate gate-b-hard-size to approval-gates'
not_contains "$STEP2B5_RC_MD" 'Gate A / discussion-round2 fallback rc `12`' 'step2b5 rc handling must remove Gate A fallback rc trigger'
not_contains "$STEP2B5_RC_MD" 'Gate B fallback rc `12`' 'step2b5 rc handling must remove Gate B fallback rc trigger'
contains "$APPROVAL_GATES_MD" 'Before executing the Gate B body, bind `_gate_b_round` from `FINAL_ROUND_NUM`, then `STEP3_REVIEW_ROUND_NUM`, then `ROUND_NUM`; fail closed if it is empty or non-numeric.' 'approval-gates must own Gate B pre-apply round binding'
contains "$APPROVAL_GATES_MD" 'Route through the same settle wrapper with `--round-num "$_gate_b_round"` without reapplying.' 'approval-gates must route post-apply resume through settle without reapply'
contains "$APPROVAL_GATES_MD" 'Bind `STEP3_RESUME_ROUND="$_gate_b_round"` before any later Step 3 resume fence.' 'approval-gates must bind Step 3 resume round after post-apply resume'
contains "$APPROVAL_GATES_MD" 'Do not jump directly to Step 3b from this post-apply resume branch' 'approval-gates must forbid direct Step 3b jump from post-apply resume'

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
