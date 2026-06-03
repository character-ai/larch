#!/usr/bin/env bash
# Structural regression guard for the /design two-tier contract.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
# shellcheck source=scripts/lib-p3119-fence-absence.sh
source "$REPO_ROOT/scripts/lib-p3119-fence-absence.sh"
SKILL_MD="$REPO_ROOT/skills/design/SKILL.md"
FLAGS_MD="$REPO_ROOT/skills/design/references/flags.md"
APPROVAL_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
PLAN_REVIEW_MD="$REPO_ROOT/skills/design/references/plan-review.md"
DISCUSSION_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
PLAN_LOOP_SH="$REPO_ROOT/skills/design/scripts/plan-review-loop.sh"
PLAN_REVIEW_LOOP_SH="$PLAN_LOOP_SH"
RUN_STEP3_SH="$REPO_ROOT/skills/design/scripts/run-step3-review.sh"
RUN_STEP3_MD="$REPO_ROOT/skills/design/scripts/run-step3-review.md"
DESIGN_POSTPLAN_EMIT_SH="$REPO_ROOT/skills/design/scripts/design-postplan-emit.sh"
PARSE_DESIGN_ARGV_SH="$REPO_ROOT/skills/design/scripts/parse-design-argv.sh"
DESIGN_PLAN_QUALITY_ASSESSOR_SH="$REPO_ROOT/skills/design/scripts/design-plan-quality-assessor.sh"
MAKEFILE="$REPO_ROOT/Makefile"
DIALEXEC_MD="$REPO_ROOT/skills/design/references/dialectic-execution.md"

fail() {
  printf 'FAIL: %s\n' "$1" >&2
  exit 1
}

contains() {
  local file="$1" needle="$2" label="$3"
  grep -Fq -- "$needle" "$file" || fail "$label"
}

absent() {
  local file="$1" needle="$2" label="$3"
  if grep -Fq -- "$needle" "$file"; then
    fail "$label"
  fi
}

contains "$SKILL_MD" '[--hard]' 'SKILL argument hint must expose --hard as the sole tier flag'
absent "$SKILL_MD" '[--simple|' 'SKILL argument hint must not restore [--simple|--hard] tier alternation'
contains "$SKILL_MD" 'The default tier is SIMPLE' 'SKILL must document default SIMPLE tier resolution'
contains "$SKILL_MD" '**Tier resolution**' 'SKILL must document non-interactive Tier resolution sub-step'
grep -Fq 'default tier: SIMPLE (no --hard)' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail 'design-init-runparams.sh must pin default-tier write-run-params reason string'
absent "$SKILL_MD" '**Tier gate**' 'SKILL must not retain retired Step 0 Tier gate sub-step'
absent "$SKILL_MD" 'cancelled-tier-gate' 'SKILL must not retain cancelled-tier-gate outcome'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
absent "$SKILL_MD" 'the tier `AskUserQuestion`' 'SKILL must not retain interactive tier AskUserQuestion gate'
absent "$SKILL_MD" 'argv tier: --simple' 'SKILL must not retain legacy argv-tier --simple reason string'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'unrecognized or disallowed leading public `--` flag is a hard error before Step 0' 'SKILL must document disallowed-public-flag rejection before Step 0'
contains "$SKILL_MD" 'before invoking the Step 0a Bash block' 'SKILL must validate public argv before session-setup'
absent "$APPROVAL_MD" 'Step 0 tier-gate' 'approval-gates.md must not retain retired Step 0 tier-gate contrast'
contains "$SKILL_MD" 'design_classification == SIMPLE' 'SKILL missing SIMPLE branch prose'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'unless `design_classification == SIMPLE`, where the user-confirmed no-sketch carve-out applies' 'SKILL missing SIMPLE Design Mindset carve-out'
contains "$SKILL_MD" 'NO_SKETCHES_CLASSIFIED_SIMPLE' 'SKILL missing SIMPLE sketch sentinel'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'Skip sketches only when `design_classification == SIMPLE`' 'SKILL missing Anti-pattern #1 SIMPLE carve-out prose'
contains "$SKILL_MD" 'This is a SIMPLE-tier design. Bias the plan toward the **smallest change that achieves the goal**.' 'SKILL missing SIMPLE designer emphasis'
contains "$SKILL_MD" 'This is a HARD-tier design. Bias the plan toward **thoroughness**.' 'SKILL missing HARD designer emphasis'
contains "$RUN_STEP3_SH" 'review-round-count.txt' 'run-step3-review.sh missing review-round counter'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
contains "$RUN_STEP3_SH" '--round-cap "$ROUND_CAP"' 'run-step3-review.sh must pass round-cap to plan-review-loop'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
absent "$RUN_STEP3_SH" '--convergence-threshold "$CONVERGENCE_THRESHOLD"' 'run-step3-review.sh must NOT forward convergence-threshold to plan-review-loop'
absent "$SKILL_MD" '--convergence-threshold' 'SKILL.md must NOT pass convergence-threshold to run-step3-review.sh'
absent "$SKILL_MD" 'LARCH_DESIGN_CONVERGENCE_THRESHOLD' 'SKILL.md must NOT reference LARCH_DESIGN_CONVERGENCE_THRESHOLD'
# shellcheck disable=SC2016 # Markdown literal intentionally checks unexpanded parameter syntax.
contains "$SKILL_MD" '--round-cap "${LARCH_DESIGN_ROUND_CAP:-5}"' 'SKILL must pass explicit round-cap to run-step3-review.sh'
TR_RUN_STEP3_SH="$REPO_ROOT/skills/design/scripts/test-run-step3-review.sh"
contains "$TR_RUN_STEP3_SH" 'driver argv matches plan-review-loop contract' \
  'test-run-step3-review.sh missing plan-review-loop integration-seam case'
_plan_forward_flags=(--design-tmpdir --plan-file --feature-file --codex-present --cursor-present --round-num --round-cap)
for _pf in "${_plan_forward_flags[@]}"; do
  grep -Fq -- "$_pf" "$PLAN_LOOP_SH" \
    || fail "plan-review-loop.sh missing $_pf in argv parser"
  grep -Fq -- "$_pf" "$RUN_STEP3_SH" \
    || fail "run-step3-review.sh missing $_pf forward to plan-review-loop"
  grep -Fq -- "$_pf" "$TR_RUN_STEP3_SH" \
    || fail "test-run-step3-review.sh integration-seam stub missing $_pf (sync with plan-review-loop.sh)"
done
contains "$RUN_STEP3_SH" '.step3-plan-review-result.env' 'run-step3-review.sh must read step3 plan-review result env'
contains "$RUN_STEP3_SH" 'result env is a symlink; ignoring it and using stdout fallback only' 'run-step3-review.sh missing symlink-safe step3 result env warning'
contains "$SKILL_MD" 'invoke-plan-validator.sh' 'SKILL missing renamed validator helper'
contains "$RUN_STEP3_SH" 'read-design-classification.sh' 'run-step3-review.sh missing classification reader'
contains "$RUN_STEP3_SH" '.step3-review-cap.env' 'run-step3-review.sh missing persisted Step 3 cap state file'
contains "$RUN_STEP3_SH" 'STEP3_REVIEW_CAP_REACHED=false' 'run-step3-review.sh missing persisted cap-false state'
contains "$RUN_STEP3_SH" 'STEP3_REVIEW_ROUND_NUM=' 'run-step3-review.sh missing persisted Step 3 round number state'
contains "$SKILL_MD" 'run-step3-review.sh' 'SKILL must invoke run-step3-review.sh'
contains "$SKILL_MD" 'step3 review result env is a symlink; refusing to source' 'SKILL must read allowlisted KVs from .step3-review-result.env'
[[ -x "$RUN_STEP3_SH" ]] || fail 'run-step3-review.sh must be executable'
[[ -f "$RUN_STEP3_MD" ]] || fail "run-step3-review.md missing: $RUN_STEP3_MD"
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'including `LOOP_STATUS=panel-failed`' 'SKILL missing panel-failed counter-consumption contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'MUST NOT persist when `TALLY_PLAN_REVIEW_STATUS=tally-error`' 'SKILL missing tally-error counter-skip contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" '`LOOP_STATUS=converged|cap-hit` — proceed to Gate B **passive-summary mode**' 'SKILL missing passive-summary branch matrix entry'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" '`LOOP_STATUS=emit-plan-failed` — treat as a Step 3 post-apply failure' 'SKILL missing emit-plan-failed branch matrix entry'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
contains "$RUN_STEP3_SH" 'review-round cap (${_round_cap}) reached for ${_tier}' 'run-step3-review.sh missing Step 3 cap breadcrumb emit'
contains "$SKILL_MD" 'skip Gate B, and jump to Step 3b/4/4b with existing artifacts' 'SKILL missing cap short-circuit Gate B bypass'
contains "$SKILL_MD" 'Gate B would otherwise re-surface stale accepted findings from an earlier round' 'SKILL missing stale-finding cap rationale'
contains "$SKILL_MD" 'The Step 3.5 continuation block below is bypassed on this path.' 'SKILL missing explicit Step 3.5 bypass prose'
contains "$SKILL_MD" 'the four primary options are **Approve final design** / **See full plan** / **Discuss further** / **Re-run review panel**' 'SKILL missing Gate C four-option prose'
contains "$SKILL_MD" 'Gate C MUST omit **Re-run review panel** and offer only **Approve final design** / **See full plan** / **Discuss further**' 'SKILL missing Gate C cap-omission prose with See full plan'
contains "$SKILL_MD" 'plan review MUST ALWAYS run the full Step 3 panel' 'SKILL missing full-panel Step 3 contract'

grep -Fq 'sketch_budget=0' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail 'design-init-runparams.sh must pin SIMPLE sketch_budget=0'
contains "$SKILL_MD" 'design-postplan-emit.sh' 'SKILL missing postplan driver quick validator skip owner'
absent "$SKILL_MD" 'invoke-plan-validator-if-not-quick.sh' 'SKILL must not reference old validator helper'
absent "$SKILL_MD" 'read-design-review-budget.sh' 'SKILL must not reference old budget reader'
absent "$SKILL_MD" 'NO_SKETCHES_CLASSIFIED_TRIVIAL' 'SKILL must not reference old trivial sentinel'
absent "$SKILL_MD" 'plan-review-quick.md' 'SKILL must not reference deleted quick review reference'
absent "$SKILL_MD" 'design-l3-velocity-notified-2670' 'SKILL must not retain Step 5d velocity comment sentinel'
contains "$SKILL_MD" 'contract drift' 'SKILL missing Step 0b contract-drift abort prose'
contains "$SKILL_MD" 'aborting before silent tier downgrade' 'SKILL missing silent tier downgrade abort pin'
contains "$SKILL_MD" 'bash scripts/test-write-run-params.sh' 'SKILL missing contract-drift repro command'
grep -Fq 'refusing to recreate it with fallback defaults' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail 'design-init-runparams.sh missing no-fallback run-params warning'
absent "$SKILL_MD" 'run-params write failed; router-flag recovery' 'SKILL must not retain old HARD fallback recovery reason'

contains "$FLAGS_MD" 'design-postplan-emit.sh' 'flags.md missing postplan driver validator contract'
contains "$FLAGS_MD" 'skipped-quick' 'flags.md missing quick validator skip contract'
contains "$FLAGS_MD" '--force-validate' 'flags.md missing discussion-round2 force-validate contract'
contains "$APPROVAL_MD" 'Cap: SIMPLE = 3, HARD = 5' 'approval-gates.md missing tier cap'
contains "$APPROVAL_MD" 'review-round cap (<cap>) reached for <tier>; skipping panel and continuing to Step 3b, Step 4, then Gate C.' 'approval-gates.md missing canonical Step 3 cap breadcrumb'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'Gate B passive-summary mode (`LOOP_STATUS=converged|cap-hit`)' 'approval-gates.md missing passive-summary section heading'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'do **not** fire an `AskUserQuestion` here — auto-continue to Step 3.6, then Step 3b, then Step 4, then Gate C' 'approval-gates.md passive-summary must be non-blocking auto-continue (no AskUserQuestion)'
contains "$APPROVAL_MD" 'do **not** halt the turn on the printed table' 'approval-gates.md passive-summary must not halt on multi-round table'
contains "$APPROVAL_MD" 'Gate C (Step 4b) is the single decision point' 'approval-gates.md passive-summary must pin Gate C as single decision point'
contains "$APPROVAL_MD" 'zero-findings short-circuit → Step 3.6 → Step 3b → Step 4 → Step 4b.' 'approval-gates.md missing zero-findings Step 3.6 forward link'
contains "$APPROVAL_MD" 'passive-summary auto-continue → Step 3.6 → Step 3b → Step 4 → Step 4b' 'approval-gates.md missing passive-summary Gate C Step 3.6 forward link'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'proceed to Step 3.6 (HARD-only plan-quality assessor; see `assessor.md`) then Step 3b' 'approval-gates.md missing shared post-apply Step 3.6 forward link'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'When `manual_gate_b=false` and `LOOP_STATUS` is neither `converged` nor `cap-hit`, execute the auto-apply path:' 'approval-gates.md missing explicit converged/cap-hit auto-apply skip guard'
contains "$APPROVAL_MD" 'Re-run review panel' 'approval-gates.md missing Gate C rerun option contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 're-fires the same Gate A `AskUserQuestion` minus the `See full plan` option, leaving exactly two options (`Ready for review` / `Discuss more`)' 'approval-gates.md missing Gate A See-full-plan re-prompt contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'If `$DESIGN_TMPDIR/plan.txt` is missing or empty on re-entry (should not happen — re-entry is post-plan by definition), print `**⚠ plan.txt missing or empty; nothing to show.**` and re-prompt with the two-option shape anyway.' 'approval-gates.md missing Gate A missing-plan recovery contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'Any Gate C re-prompt after `Other` must preserve those three at-cap options' 'approval-gates.md missing Gate C cap re-prompt omission contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" '- **See full plan** — Print the current `$DESIGN_TMPDIR/plan.txt` into chat under a `## Final Design Plan` header' 'approval-gates.md missing Gate C See-full-plan bullet'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'If `$DESIGN_TMPDIR/plan.txt` is missing or empty when the user picks the structured `See full plan` option (for example after the warning-only presentation path), print `**⚠ plan.txt missing or empty; nothing to show.**` and still re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option.' 'approval-gates.md missing Gate C structured missing-plan recovery contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'the `Other` re-prompt preserves the **same option set unchanged**' 'approval-gates.md missing Gate C Other-path unchanged-option-set contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'when `plan.txt` is missing or empty, print `**⚠ plan.txt missing or empty; nothing to show.**` instead and still re-fire the same prompt' 'approval-gates.md missing Gate C Other missing-plan recovery contract'
contains "$APPROVAL_MD" 'offer this option only when the current review-round count is still below the tier cap' 'approval-gates.md missing Gate C cap-aware rerun contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$PLAN_REVIEW_MD" 'Step 3 always runs the full panel via `plan-review-loop.sh`' 'plan-review.md missing full-panel consumer line'
contains "$PLAN_REVIEW_MD" 'injects the SIMPLE-emphasis or HARD-emphasis text immediately after the role line' 'plan-review.md missing tier-emphasis injection contract'
contains "$PLAN_REVIEW_MD" 'When in doubt between YES and EXONERATE, prefer EXONERATE.' 'plan-review.md missing voter-bias proportionality pin'
contains "$PLAN_REVIEW_MD" 'Treat any suggested remedy in the item body as *informational only*' 'plan-review.md missing OOS remedy informational-only pin'
contains "$PLAN_REVIEW_MD" 'Security-tagged findings are held locally and NEVER written to this public OOS issue artifact' 'plan-review.md missing SECURITY.md OOS exclusion pin'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$PLAN_REVIEW_MD" 'Security-tagged accepted OOS findings are held locally per SECURITY.md and are NOT included in `oos.md`.' 'plan-review.md missing SECURITY.md oos.md exclusion pin'
contains "$DISCUSSION_MD" 'design-postplan-emit.sh' 'discussion-rounds.md missing postplan validator driver helper'

if grep -Eq 'grep .*review-round-count\.txt|review-round-count\.txt.*grep' "$PLAN_LOOP_SH"; then
  fail 'plan-review-loop.sh must not grep review-round-count.txt'
fi
contains "$PLAN_LOOP_SH" '--round-num is a stateless integer supplied by the caller' 'plan-review-loop.sh missing stateless round comment'

absent "$MAKEFILE" 'test-read-design-review-budget-invoke' 'Makefile must not reference deleted read-design-review-budget harness'

# Gate B auto-apply / --manual pins (preserved from #3009, adapted to v2 SIMPLE/HARD).
contains "$APPROVAL_MD" '### Apply-all body' 'approval-gates.md missing Apply-all body heading'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'Execute `### Apply-all body` verbatim' 'approval-gates.md missing Apply-all body delegate prose'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$FLAGS_MD" '`--manual` / `-m`:' 'flags.md missing --manual/-m bullet anchor'
absent "$APPROVAL_MD" 'no auto-apply' 'approval-gates.md: stale "no auto-apply" prose contradicts default auto-apply rule'
absent "$SKILL_MD"    'no auto-apply' 'SKILL.md: stale "no auto-apply" prose contradicts default auto-apply rule'
absent "$APPROVAL_MD" 'user is always prompted' 'approval-gates.md: stale "user is always prompted" prose contradicts default auto-apply rule'
absent "$SKILL_MD"    'user is always prompted' 'SKILL.md: stale "user is always prompted" prose contradicts default auto-apply rule'
absent "$APPROVAL_MD" 'Gate B always prompts' 'approval-gates.md: stale "Gate B always prompts" prose contradicts default auto-apply rule'
absent "$SKILL_MD"    'Gate B always prompts' 'SKILL.md: stale "Gate B always prompts" prose contradicts default auto-apply rule'
absent "$APPROVAL_MD" 'fail-closed to manual' 'approval-gates.md: stale "fail-closed to manual" prose contradicts degraded-mode auto-apply default'
absent "$SKILL_MD"    'fail-closed to manual' 'SKILL.md: stale "fail-closed to manual" prose contradicts degraded-mode auto-apply default'

# Check 15d: design SKILL must not chat-print token/timing summaries.
if grep -nF 'token-report.sh --summary' "$SKILL_MD" | grep -q .; then
  fail "(15d) skills/design/SKILL.md must not invoke token-report.sh --summary"
fi
if grep -nF 'timing-report.sh --summary' "$SKILL_MD" | grep -q .; then
  fail "(15d) skills/design/SKILL.md must not invoke timing-report.sh --summary"
fi

# Check 14: design ACTION dispatcher pins. The focus-area enum must remain in
# SKILL.md because CI and prompt rendering scan the inline reviewer launch
# blocks, while scriptable mechanics route through ACTION records.
focus_anchor_count=$(grep -Fc 'Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security' "$SKILL_MD")
[[ "$focus_anchor_count" == "1" ]] \
  || fail "(14a) SKILL.md must keep exactly 1 focus-area enum anchor comment; found $focus_anchor_count"
grep -Fq 'design-postplan-emit.sh' "$SKILL_MD" \
  || fail "(14b1) SKILL.md missing design-postplan-emit.sh invocation"
grep -Fq 'ACTION=FINALIZE' "$SKILL_MD" \
  || fail "(14b3) SKILL.md missing ACTION=FINALIZE emission"
grep -Fq 'design-driver.sh' "$SKILL_MD" \
  || fail "(14b4) SKILL.md missing design-driver.sh dispatcher invocation"
grep -Fq 'run-step3-review.sh' "$SKILL_MD" \
  || fail "(14c0) SKILL.md missing run-step3-review.sh Step 3 driver invocation"
grep -Fq 'set +e' "$RUN_STEP3_SH" \
  || fail "(14c0b) run-step3-review.sh missing set +e guard around plan-review-loop.sh"
grep -Fq '_plan_review_rc=$?' "$SKILL_MD" \
  || fail "(14c0c) SKILL.md missing _plan_review_rc capture for run-step3-review.sh"
# shellcheck disable=SC2016 # Markdown/bash excerpt literal; $DESIGN_TMPDIR must not expand here.
contains "$SKILL_MD" '-f "$DESIGN_TMPDIR/.step3-review-result.env"' 'SKILL must source .step3-review-result.env when present'
contains "$SKILL_MD" 'WARN) printf' 'SKILL must re-emit WARN lines from step3 review handoff'
contains "$SKILL_MD" 'missing or invalid LOOP_STATUS after run-step3-review.sh; treating plan review as panel-failed' 'SKILL must default missing LOOP_STATUS to panel-failed (not hard abort on driver exit 1)'
contains "$SKILL_MD" 'configuration error (exit 2)' 'SKILL must warn on run-step3-review.sh exit 2'
grep -Fq 'scout-plan-archetypes-wrapper.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c1) plan-review-loop.sh missing scout-plan-archetypes-wrapper.sh"
grep -Fq 'dispatch-plan-review-panel.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c2) plan-review-loop.sh missing dispatch-plan-review-panel.sh"
grep -Fq 'PANEL_PATHS_FILE' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c3) plan-review-loop.sh missing PANEL_PATHS_FILE handling"
[[ -x "$PLAN_REVIEW_LOOP_SH" ]] \
  || fail "(14c4) plan-review-loop.sh must be executable"
PR_LOOP_MD="$REPO_ROOT/skills/design/scripts/plan-review-loop.md"
[[ -f "$PR_LOOP_MD" ]] || fail "(14c5) plan-review-loop.md missing: $PR_LOOP_MD"
grep -Fqe '--input-mode plan' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c6) plan-review-loop.sh missing --input-mode plan aggregate invocation"
grep -Fq 'tally-plan-review.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c7) plan-review-loop.sh missing tally-plan-review.sh"
grep -Fq 'dispatch-plan-voters.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c8) plan-review-loop.sh missing dispatch-plan-voters.sh"
grep -Fq 'aggregate-findings.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c9) plan-review-loop.sh missing aggregate-findings.sh"
grep -Fq 'check-mid-run-dirty-tree.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c10) plan-review-loop.sh missing check-mid-run-dirty-tree.sh"
grep -Fq 'compose-collector-failure-log.sh' "$PLAN_REVIEW_LOOP_SH" \
  || fail "(14c11) plan-review-loop.sh missing compose-collector-failure-log.sh"
grep -Fq 'launch-claude-review.sh' "$REPO_ROOT/scripts/dispatch-plan-voters.sh" \
  || fail "(14c12) dispatch-plan-voters.sh missing launch-claude-review.sh (Voter 1)"
TR_LOOP_SH="$REPO_ROOT/skills/design/scripts/test-plan-review-loop.sh"
TR_LOOP_MD="$REPO_ROOT/skills/design/scripts/test-plan-review-loop.md"
[[ -x "$TR_LOOP_SH" ]] || fail "(14c13) test-plan-review-loop.sh missing or not executable"
[[ -f "$TR_LOOP_MD" ]] || fail "(14c14) test-plan-review-loop.md missing"

[[ -x "$PARSE_DESIGN_ARGV_SH" ]] || fail 'parse-design-argv.sh must be executable'
contains "$PARSE_DESIGN_ARGV_SH" 'VALIDATION_ERROR=' 'parse-design-argv.sh missing validation-error output'
contains "$PARSE_DESIGN_ARGV_SH" 'POSITIONAL_KIND=' 'parse-design-argv.sh missing positional-kind output'
grep -Fq 'parse-design-argv.sh' "$SKILL_MD" || fail 'SKILL.md missing parse-design-argv.sh Step 0-pre wiring'
if ! grep -Fq 'POSITIONAL_KIND' "$SKILL_MD" || grep -Fq 'remaining tokens after flags' "$SKILL_MD"; then
  fail 'Step 0b must consume POSITIONAL_KIND from 0-pre, not re-parse argv tail'
fi
step0pre_block=$(awk '/^### 0-pre /,/^### 0a /' "$SKILL_MD")
printf '%s\n' "$step0pre_block" | grep -Fq 'set +e' \
  || fail 'Step 0-pre fence missing set +e around parse-design-argv.sh capture'
printf '%s\n' "$step0pre_block" | grep -Fq '_argv_rc=$?' \
  || fail 'Step 0-pre fence missing explicit _argv_rc capture'
printf '%s\n' "$step0pre_block" | grep -Fq 'VALIDATION_ERROR' \
  || fail 'Step 0-pre fence missing VALIDATION_ERROR handling'
printf '%s\n' "$step0pre_block" | grep -Fq '<PUBLIC_ARGV_WORDS>' \
  || fail 'Step 0-pre fence must invoke parse-design-argv.sh via <PUBLIC_ARGV_WORDS> substitution'
if printf '%s\n' "$step0pre_block" | grep -Fq '\$ARGUMENTS'; then
  fail 'Step 0-pre fence must not re-parse $ARGUMENTS'
fi
printf '%s\n' "$step0pre_block" | grep -Fq 'unexpanded template literal' \
  || fail 'Step 0-pre must reject unexpanded CLAUDE_PLUGIN_ROOT template literal'
printf '%s\n' "$step0pre_block" | grep -Fq 'parse-design-argv.sh not executable' \
  || fail 'Step 0-pre must verify parse-design-argv.sh is executable before invoke'
contains "$PARSE_DESIGN_ARGV_SH" 'assert_safe_kv_value' 'parse-design-argv.sh missing newline guard on emitted values'

DESIGN_DRIVER_SH="$REPO_ROOT/skills/design/scripts/design-driver.sh"
[[ -x "$DESIGN_POSTPLAN_EMIT_SH" ]] || fail "design-postplan-emit.sh must be executable"
contains "$DESIGN_POSTPLAN_EMIT_SH" 'ACTION=EMIT_PLAN' 'design-postplan-emit.sh missing EMIT_PLAN dispatch'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'snapshot-plan-round.sh' 'design-postplan-emit.sh missing snapshot helper call'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'write-original' 'design-postplan-emit.sh missing write-original call'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'invoke-plan-validator.sh' 'design-postplan-emit.sh missing validator helper call'
contains "$DESIGN_POSTPLAN_EMIT_SH" '_postplan_resolve_issue' 'design-postplan-emit.sh missing issue resolver'
contains "$DESIGN_POSTPLAN_EMIT_SH" '_postplan_pause_checkpoint' 'design-postplan-emit.sh missing pause checkpoint'
contains "$DESIGN_POSTPLAN_EMIT_SH" '_postplan_write_result_and_emit' 'design-postplan-emit.sh missing result flush helper'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'set +e' 'design-postplan-emit.sh missing child set +e capture'
postplan_emit_line=$(grep -nF 'ACTION=EMIT_PLAN' "$DESIGN_POSTPLAN_EMIT_SH" | head -1 | cut -d: -f1 || true)
postplan_val_line=$(grep -nF 'invoke-plan-validator.sh' "$DESIGN_POSTPLAN_EMIT_SH" | head -1 | cut -d: -f1 || true)
[[ -n "$postplan_emit_line" && -n "$postplan_val_line" && "$postplan_emit_line" -le "$postplan_val_line" ]]   || fail "design-postplan-emit.sh must dispatch EMIT at or before validator"
contains "$SKILL_MD" '.design-postplan-emit-result.env' 'SKILL.md missing postplan result env read'
# shellcheck disable=SC2016 # Markdown literal; parameter syntax must remain unexpanded.
contains "$SKILL_MD" '<<<"${_postplan_out:-}"' 'SKILL.md missing postplan stdout fallback merge'
contains "$SKILL_MD" 'design-postplan-emit.sh configuration error (exit 2)' 'SKILL.md missing postplan exit-2 abort prose'
# shellcheck disable=SC2016 # Markdown literal; $PPID must remain unexpanded.
contains "$SKILL_MD" 'current-design-env-$PPID.sh' 'SKILL.md Step 2b postplan fence missing canonical prelude'
DESIGN_POSTPLAN_STEP2B=$(awk '/^<!-- step:2b /,/^### Step 2b\.5/' "$SKILL_MD")
if printf '%s\n' "$DESIGN_POSTPLAN_STEP2B" | grep -Fq 'ACTION=EMIT_PLAN'; then
  fail "(FINDING_1) Step 2b block must not retain bare ACTION=EMIT_PLAN outside shared validator failure prose"
fi
step1e_block=$(awk '/Optional trailer guard \(Gate A re-entry rewrites\)/,/^<!-- step:2a /' "$SKILL_MD")
printf '%s\n' "$step1e_block" | grep -Fq 'design-postplan-emit.sh' \
  || fail "(14c14i) Gate A optional-trailer guard missing design-postplan-emit.sh"
printf '%s\n' "$step1e_block" | grep -Fq 'Plan command validator failure' \
  || fail "(14c14i) Gate A optional-trailer guard missing shared defects-found routing"
grep -Fq 'VALIDATE_PLAN_COMMANDS' "$DESIGN_DRIVER_SH" \
  || fail "(14b5) design-driver.sh missing VALIDATE_PLAN_COMMANDS"
grep -Fq 'validate-plan.sh' "$DESIGN_DRIVER_SH" \
  || fail "(14b6) design-driver.sh missing validate-plan.sh dispatch arm"
grep -Fq 'ACTION=VALIDATE_PLAN_COMMANDS' "$SKILL_MD" \
  || fail "(14b7) SKILL.md missing ACTION=VALIDATE_PLAN_COMMANDS"
grep -Fq 'Fix-and-retry' "$SKILL_MD" \
  || fail "(14b8) SKILL.md missing Fix-and-retry validator option label"
grep -Fq 'Override' "$SKILL_MD" \
  || fail "(14b9a) SKILL.md missing Override validator option label"
grep -Fq 'Cancel' "$SKILL_MD" \
  || fail "(14b9b) SKILL.md missing Cancel validator option label"
step2b_mark=$(grep -nF 'mark "design Step 2b — plan"' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
postplan_line=$(awk -v s="$step2b_mark" 'NR>s && /design-postplan-emit\.sh/ {print NR; exit}' "$SKILL_MD" || true)
step2b5_line=$(awk -v s="$step2b_mark" 'NR>s && /### Step 2b\.5/ {print NR; exit}' "$SKILL_MD" || true)
[[ -n "$step2b_mark" && -n "$postplan_line" && -n "$step2b5_line" && "$step2b5_line" -gt "$postplan_line" ]] \
  || fail "(14b10) design-postplan-emit.sh must precede Step 2b.5 in Step 2b block"

AG_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
DR_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
[[ -f "$AG_MD" ]] || fail "(14c14a) approval-gates.md missing: $AG_MD"
[[ -f "$DR_MD" ]] || fail "(14c14b) discussion-rounds.md missing: $DR_MD"
grep -Fq 'design-postplan-emit.sh' "$AG_MD" \
  || fail "(14c14c) approval-gates.md missing design-postplan-emit.sh pin"
grep -Fq 'VALIDATE_STATUS' "$AG_MD" \
  || fail "(14c14d) approval-gates.md must reference VALIDATE_STATUS (validator routing through driver)"
postplan_before_size_ag=$(awk '/^### Shared post-apply pipeline/ { in_section=1 } in_section && /design-postplan-emit\.sh/ && !e { e=NR } in_section && e && /Step 2b\.5/ && !v { v=NR } /^### Gate B plan revision/ { in_section=0 } END { if (e && v) print (e <= v) ? 1 : 0; else print 0 }' "$AG_MD")
[[ "$postplan_before_size_ag" == "1" ]] \
  || fail "(14c14e) approval-gates.md must mention design-postplan-emit.sh at or before Step 2b.5"
grep -Fq 'design-postplan-emit.sh' "$DR_MD" \
  || fail "(14c14f) discussion-rounds.md missing design-postplan-emit.sh pin"
grep -Fq -- '--force-validate' "$DR_MD" \
  || fail "(14c14g) discussion-rounds.md missing --force-validate pin"
postplan_before_size_dr=$(awk '/\*\*Plan revision authority\*\*/ { in_section=1 } in_section && /design-postplan-emit\.sh/ && !e { e=NR } in_section && e && /Step 2b\.5/ && !v { v=NR } /^## Cap/ { in_section=0 } END { if (e && v) print (e <= v) ? 1 : 0; else print 0 }' "$DR_MD")
[[ "$postplan_before_size_dr" == "1" ]] \
  || fail "(14c14h) discussion-rounds.md must mention design-postplan-emit.sh at or before Step 2b.5"

# Check 16: dialectic waterfall + per-side assignment contract pins (#2620).
DIALPROTO_MD="$REPO_ROOT/skills/shared/dialectic-protocol.md"
DEBATE_MD="$REPO_ROOT/skills/design/references/dialectic-debate.md"
TIMING_KINDS_SH="$REPO_ROOT/scripts/lib-timing-kinds.sh"
grep -Fq '## Per-side waterfall retry' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing '## Per-side waterfall retry' section header"
grep -Fq 'Debater quorum gate (six tags)' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing six-tag eligibility gate anchor"
grep -Fq '<steelman>' "$DIALPROTO_MD" \
  || fail "(16) dialectic-protocol.md missing <steelman> in six-tag gate text"
grep -Fq '5. **Per-side waterfall retry**' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing step 5 Per-side waterfall retry header"
grep -Fq 'waterfall' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing waterfall token (step 5 contract)"
grep -Fq '1. **Per-side external tool assignment**' "$DIALEXEC_MD" \
  || fail "(16) dialectic-execution.md missing step 1 per-side external tool assignment header"
grep -Fq 'OUTPUT FORMAT' "$DEBATE_MD" \
  || fail "(16) dialectic-debate.md missing OUTPUT FORMAT header"
grep -Fq 'SELF-CHECK BEFORE STOPPING' "$DEBATE_MD" \
  || fail "(16) dialectic-debate.md missing SELF-CHECK BEFORE STOPPING directive"
grep -Fq '2nd-retry' "$SKILL_MD" \
  || fail "(16) design SKILL.md NEVER #2 missing 2nd-retry Claude exception token"
for kind in \
  cursor-debate-thesis-retry1 \
  cursor-debate-antithesis-retry1 \
  codex-debate-thesis-retry1 \
  codex-debate-antithesis-retry1 \
  claude-debate-thesis-retry2 \
  claude-debate-antithesis-retry2
do
  grep -Fq "$kind" "$TIMING_KINDS_SH" \
    || fail "(16) scripts/lib-timing-kinds.sh missing timing kind: $kind"
done

grep -Fq $'2b\tfull plan' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 2b\\tfull plan row"
grep -Fq $'2b.5\tplan size' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 2b.5\\tplan size row"
grep -Fq $'5\tfinalize' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 5\\tfinalize row"
grep -Fq $'6\tcleanup' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(15b) step-name-registry.tsv missing 6\\tcleanup row"
grep -Fq '> **🔶 /design 5: finalize**' "$SKILL_MD" \
  || fail "(15b) SKILL.md missing /design 5 finalize breadcrumb"
grep -Fq '> **🔶 /design 6: cleanup**' "$SKILL_MD" \
  || fail "(15b) SKILL.md missing /design 6 cleanup breadcrumb"
step5b_line=$(grep -nF '### 5b — File accepted OOS issues' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
step5c_line=$(grep -nF "### 5c — Write \`larch:plan\` to GitHub + publish" "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step5b_line" && -n "$step5c_line" ]] || fail "(15b) missing Step 5b or 5c sub-step headers"
if (( step5b_line >= step5c_line )); then
  fail "(15b) Step 5b must appear before Step 5c in SKILL.md"
fi
red_line=$(awk -v s="$step5c_line" 'NR>s && /redact-secrets\.sh/ && /composed-plan\.md/ {print NR; exit}' "$SKILL_MD" || true)
val5=$(awk -v s="$step5c_line" 'NR>s && /invoke-plan-validator\.sh/ && /composed-plan\.md/ {print NR; exit}' "$SKILL_MD" || true)
[[ -n "$red_line" && -n "$val5" && "$val5" -lt "$red_line" ]] \
  || fail "(14b11) Step 5c validator must appear before redact-secrets on composed-plan.md"
# shellcheck disable=SC2016  # literal backticks + $DESIGN_TMPDIR token must match SKILL.md prose
needle='preserve `$DESIGN_TMPDIR`, skip Step 6 cleanup'
grep -Fq "$needle" "$SKILL_MD" \
  || fail "(14b12) Step 5c validator cancel must preserve tmpdir and skip cleanup"
grep -Fq '5c.5→5c.7→5c.8→6' "$SKILL_MD" \
  || fail "(15b) anti-halt reminder must mention 5c.5→5c.7→5c.8→6 step boundary (intra-Step-5 through rename)"

DESIGN_PUBLISH_SH="$REPO_ROOT/skills/design/scripts/design-publish.sh"
[[ -x "$DESIGN_PUBLISH_SH" ]] || fail "design-publish.sh must be executable"
publish_plan_line=$(grep -nF 'plan-block-write.sh' "$DESIGN_PUBLISH_SH" | head -1 | cut -d: -f1 || true)
publish_upsert_line=$(grep -nF 'upsert-diagrams-comment.sh' "$DESIGN_PUBLISH_SH" | head -1 | cut -d: -f1 || true)
publish_log_line=$(grep -nF 'design-log-publish.sh' "$DESIGN_PUBLISH_SH" | head -1 | cut -d: -f1 || true)
[[ -n "$publish_plan_line" && -n "$publish_upsert_line" && -n "$publish_log_line" && "$publish_plan_line" -lt "$publish_upsert_line" && "$publish_upsert_line" -lt "$publish_log_line" ]] \
  || fail "(15b) design-publish.sh must call plan-block-write.sh before upsert-diagrams-comment.sh before design-log-publish.sh"
grep -Fq 'architecture-diagram.skipped' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must handle architecture-diagram.skipped sentinel"
grep -Fq -- '--clear-architecture' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must invoke --clear-architecture when skipped sentinel present"
step3b_line=$(grep -nF '<!-- step:3b' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
step4_line=$(grep -nF '<!-- step:4 ' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step3b_line" && -n "$step4_line" ]] || fail "(15b) missing Step 3b or Step 4 marker"
step3b_between=$(sed -n "$((step3b_line + 1)),$((step4_line - 1))p" "$SKILL_MD")
grep -Fq 'architecture-diagram.skipped' <<<"$step3b_between" \
  || fail "(15b) Step 3b must document architecture-diagram.skipped sentinel creation"
# Check 17: Step 5b /larch:issue summary-halt guardrails (#2681).
ORCHESTRATOR_NEVER_MD="$REPO_ROOT/skills/shared/orchestrator-never.md"
[[ -f "$ORCHESTRATOR_NEVER_MD" ]] || fail "(17) orchestrator-never.md missing: $ORCHESTRATOR_NEVER_MD"
grep -Fq '5→5a→5b→5c.1→5c.5→5c.7→5c.8→6' "$SKILL_MD" \
  || fail "(17) anti-halt reminder missing intra-Step-5 sub-step enumeration"
grep -Fq "NEVER treat a sub-skill's terminal output as the parent skill's terminal output" "$ORCHESTRATOR_NEVER_MD" \
  || fail "(17) orchestrator-never.md missing sub-skill vs parent-skill terminal-output NEVER literal"
grep -Fq 'NEVER poll a background task by reading its output file once per turn' "$ORCHESTRATOR_NEVER_MD" \
  || fail "(17) orchestrator-never.md missing per-turn-polling NEVER literal"
step5_between=$(sed -n "$((step5b_line + 1)),$((step5c_line - 1))p" "$SKILL_MD")
# Pin `/larch:issue` to the continuation-banner line (not merely anywhere in the 5b→5c window).
grep -Fq $'> **Continue to Step 5c IMMEDIATELY.** The `/larch:issue` Skill tool' <<<"$step5_between" \
  || fail "(17) Step 5b→5c continuation banner missing or /larch:issue not on the same line as the banner"

# Check FINDING_21 (#2670): plan-size thresholds + --partition documentation pins.
grep -Fq "| \`-p\` / \`--partition\` |" "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md compact flag table missing -p/--partition row"
grep -Fq '[-p|--partition]' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md argument-hint missing [-p|--partition]"
grep -Fq '[--brainstorm]' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md argument-hint missing [--brainstorm]"
grep -Fq "\`-p\`, \`--partition\`" "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md public argv allowlist missing -p/--partition"
# shellcheck disable=SC2016 # Markdown literal; backticks are SKILL.md prose, not command substitution
grep -Fq '`--partition`, `--brainstorm`, `--manual`, `-m`, `--no-dedup`, and `--run-id`' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md public argv allowlist missing --brainstorm/--manual sequence"
grep -Fq '### Step 2b.5 — Plan-size threshold check' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md missing Step 2b.5 header"
step2b_block=$(awk '/^<!-- step:2b /,/^<!-- step:3 /' "$SKILL_MD")
postplan_line=$(printf '%s\n' "$step2b_block" | grep -nF 'design-postplan-emit.sh' | head -1 | cut -d: -f1 || true)
chk_line=$(printf '%s\n' "$step2b_block" | grep -nF 'skills/design/scripts/check-plan-size.sh' | head -1 | cut -d: -f1 || true)
[[ -n "$postplan_line" && -n "$chk_line" ]] || fail "(FINDING_21) could not locate design-postplan-emit.sh / check-plan-size.sh inside Step 2b block"
if ! [[ "$chk_line" -gt "$postplan_line" ]]; then
  fail "(FINDING_21) check-plan-size.sh must appear after design-postplan-emit.sh inside Step 2b block"
fi
grep -Fq '## Plan Size — Hard Trigger' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md missing hard-trigger plan-size header"
grep -Fq '(no **Continue** option — hard triggers' "$SKILL_MD" \
  || fail "(FINDING_21) SKILL.md hard branch must document no-Continue invariant"
DISCUSSION_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
grep -Fq 'Step 1c sprawl heuristic' "$DISCUSSION_MD" \
  || fail "(FINDING_21) discussion-rounds.md missing Step 1c sprawl hook"
grep -Fq 'per Step 1d invocation' "$DISCUSSION_MD" \
  || fail "(FINDING_21) discussion-rounds.md missing Step 1d sprawl-once cap"
grep -Fq 'semantic sprawl heuristic' "$DISCUSSION_MD" \
  || fail "(FINDING_21) discussion-rounds.md missing semantic sprawl heuristic prose"
APPROVAL_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
grep -Fq 'Step 2b.5' "$APPROVAL_MD" \
  || fail "(FINDING_21) approval-gates.md missing Step 2b.5 reference after Gate B EMIT_PLAN"
grep -Fq 'SOFT_ADVISORY=' "$SKILL_MD" \
  || fail "(3175) SKILL.md Step 2b.5 must parse SOFT_ADVISORY"
grep -Fq 'DIFF_ADDED=' "$SKILL_MD" \
  || fail "(3175) SKILL.md Step 2b.5 must parse DIFF_ADDED"
grep -Fq 'DIFF_DELETED=' "$SKILL_MD" \
  || fail "(3175) SKILL.md Step 2b.5 must parse DIFF_DELETED"
grep -Fq 'MECHANICAL_CHURN=' "$SKILL_MD" \
  || fail "(3175) SKILL.md Step 2b.5 must parse MECHANICAL_CHURN"
grep -Fq 'plan-body gate still requires Split/Cancel' "$SKILL_MD" \
  || fail "(3175) SKILL.md must document plan-body hard + SOFT_ADVISORY combined advisory"
grep -Fq 'diff_added' "$SKILL_MD" \
  || fail "(3175) SKILL.md missing diff_added preservation/recompute language"
grep -Fq 'diff_deleted' "$SKILL_MD" \
  || fail "(3175) SKILL.md missing diff_deleted preservation language"
grep -Fq 'mechanical_churn' "$SKILL_MD" \
  || fail "(3175) SKILL.md missing mechanical_churn preservation language"
grep -Fq 'gate-b-dedup-plan.sh' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing mechanical gate-b-dedup-plan.sh post-apply hook"
grep -Fq "gate-b-dedup-plan.sh\" --design-tmpdir \"\$DESIGN_TMPDIR\" --snapshot-trailers" "$SKILL_MD" \
  || fail "(3175) SKILL.md Gate A/B optional-trailer guard missing --snapshot-trailers hook"
grep -Fq 'gate-b-dedup-plan.sh --dedup' "$SKILL_MD" \
  || fail "(3175) SKILL.md Gate A/B optional-trailer guard missing --dedup hook"
grep -Fq -- '--snapshot-trailers' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing --snapshot-trailers hook"
grep -Fq -- '--dedup' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing --dedup hook"
grep -Fq 'diff_added' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing diff_added preservation language"
grep -Fq -- '--snapshot-trailers' "$DISCUSSION_MD" \
  || fail "(3175) discussion-rounds.md missing --snapshot-trailers hook"
grep -Fq -- '--dedup' "$DISCUSSION_MD" \
  || fail "(3175) discussion-rounds.md missing --dedup hook"
grep -Fq 'mechanical_churn' "$DISCUSSION_MD" \
  || fail "(3175) discussion-rounds.md missing mechanical_churn preservation language"
FLAGS_MD="$REPO_ROOT/skills/design/references/flags.md"
grep -Fq 'diff_deleted' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing diff_deleted preservation language"
grep -Fq 'diff_deleted' "$DISCUSSION_MD" \
  || fail "(3175) discussion-rounds.md missing diff_deleted preservation language"
grep -Fq 'diff_deleted' "$FLAGS_MD" \
  || fail "(3175) flags.md missing diff_deleted preservation language"
# shellcheck disable=SC2016 # Markdown literal; backticks are prose, not command substitution
grep -Fq 'before `ACTION=EMIT_PLAN`' "$APPROVAL_MD" \
  || fail "(3175) approval-gates.md missing validate-before-EMIT_PLAN guard"
# shellcheck disable=SC2016 # Markdown literal; backticks are prose, not command substitution
grep -Fq 'before `ACTION=EMIT_PLAN`' "$DISCUSSION_MD" \
  || fail "(3175) discussion-rounds.md missing validate-before-EMIT_PLAN guard"
grep -Fq 'lib-plan-optional-trailers' "$REPO_ROOT/skills/design/scripts/revise-plan-with-waterfall.sh" \
  || fail "(3175) revise-plan-with-waterfall.sh must source shared optional-trailer lib"
grep -Fq 'lib-plan-optional-trailers' "$REPO_ROOT/skills/design/scripts/plan-review-loop.sh" \
  || fail "(3175) plan-review-loop.sh must source shared optional-trailer lib"
grep -Fq 'lib-plan-optional-trailers' "$REPO_ROOT/skills/design/scripts/check-plan-size.sh" \
  || fail "(3175) check-plan-size.sh must source shared optional-trailer lib"
# Check 19 (#2754): --brainstorm / Step 1d.5 / run-params / plan-review feature-context pins.
BRAINSTORM_MD="$REPO_ROOT/skills/design/references/brainstorm.md"
BRAINSTORM_PROMPTS="$REPO_ROOT/skills/design/references/brainstorm-prompts.md"
[[ -f "$BRAINSTORM_MD" ]] || fail "(2754) brainstorm.md missing"
[[ -f "$BRAINSTORM_PROMPTS" ]] || fail "(2754) brainstorm-prompts.md missing"
# shellcheck disable=SC2016 # Markdown table cell literal
grep -Fq '| `--brainstorm` |' "$SKILL_MD" \
  || fail "(2754) SKILL.md compact flag table missing --brainstorm row"
grep -Fq '<!-- step:1d.5 — Brainstorm Panel -->' "$SKILL_MD" \
  || fail "(2754) SKILL.md missing Step 1d.5 anchor"
grep -Fq '> **🔶 /design 1d.5: brainstorm**' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing 1d.5 brainstorm breadcrumb"
grep -Fq '⏩ 1d.5: brainstorm — skipped (already complete; .brainstorm-done present)' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing sentinel-hit skip breadcrumb"
grep -Fq $'1d.5\tbrainstorm' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(2754) step-name-registry.tsv missing 1d.5 brainstorm row"
grep -Fq '<BRAINSTORM_FRAMING_PROMPT>' "$BRAINSTORM_PROMPTS" \
  || fail "(2754) brainstorm-prompts.md missing <BRAINSTORM_FRAMING_PROMPT>"
grep -Fq '<BRAINSTORM_SCOPE_PROMPT>' "$BRAINSTORM_PROMPTS" \
  || fail "(2754) brainstorm-prompts.md missing <BRAINSTORM_SCOPE_PROMPT>"
grep -Fq '<BRAINSTORM_PRAGMATIC_PROMPT>' "$BRAINSTORM_PROMPTS" \
  || fail "(2754) brainstorm-prompts.md missing <BRAINSTORM_PRAGMATIC_PROMPT>"
# shellcheck disable=SC2016 # flags.md list marker uses backticks
grep -Fq '`--brainstorm`:' "$FLAGS_MD" \
  || fail "(2754) flags.md missing --brainstorm bullet anchor"
grep -Fq '1c→1d→1d.5→1d.7→2a' "$SKILL_MD" \
  || fail "(2754) SKILL.md anti-halt sequence missing 1d.5→1d.7→2a transition"
grep -Fq 'MANDATORY — READ ENTIRE FILE' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing MANDATORY directive"
grep -Fq 'skills/design/references/brainstorm-prompts.md' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing brainstorm-prompts.md path literal"
grep -Fq 'ScheduleWakeup' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing ScheduleWakeup prohibition anchor"
# Stage 4 (#3119): Family-B fence shape must stay absent from design orchestrator docs.
assert_p3119_family_b_fence_absent "$SKILL_MD" "SKILL.md"
assert_p3119_family_b_fence_absent "$BRAINSTORM_MD" "brainstorm.md"
assert_p3119_family_b_fence_absent "$DIALEXEC_MD" "dialectic-execution.md"
assert_p3119_family_b_fence_absent "$PLAN_REVIEW_MD" "plan-review.md"
assert_p3119_family_b_fence_absent "$DIALPROTO_MD" "dialectic-protocol.md"
# shellcheck disable=SC2016 # SKILL.md bash excerpt; quotes are literal
grep -Fq -- '--brainstorm-requested "$brainstorm_requested"' "$SKILL_MD" \
  || fail "(2754) SKILL.md design-init-runparams invocation missing --brainstorm-requested"
# shellcheck disable=SC2016 # SKILL.md bash excerpt
grep -Fq -- '[[ "$PARTITION_REQUESTED" == true || "$BRAINSTORM_REQUESTED" == true || "$MANUAL_REQUESTED" == true ]]' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail "(2754) design-init-runparams.sh recovery guard missing partition OR brainstorm OR manual"
# shellcheck disable=SC2016 # jq filter literal
grep -Fq -- '.brainstorm_requested = (.brainstorm_requested == true or $merge_b)' "$REPO_ROOT/skills/design/scripts/design-init-runparams.sh" \
  || fail "(2754) design-init-runparams.sh jq merge missing brainstorm_requested arm"
grep -Fq '⏩ 1d.5: brainstorm — skipped' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing skip breadcrumb literal"
grep -Fq 'plan-review-feature-context.txt' "$REPO_ROOT/skills/design/scripts/plan-review-loop.sh" \
  || fail "(2754) plan-review-loop.sh missing plan-review-feature-context merge path"
for _bk in cursor-brainstorm codex-brainstorm; do
  grep -Fq "$_bk" "$TIMING_KINDS_SH" \
    || fail "(2754) scripts/lib-timing-kinds.sh missing timing kind: $_bk"
done

# Check 20 (#2974): Step 1d.7 outline approval replaces first-time Gate A.
DESIGN_OUTLINE_MD="$REPO_ROOT/skills/design/references/design-outline.md"
[[ -f "$DESIGN_OUTLINE_MD" ]] || fail "(2974) design-outline.md missing"
line_1d5=$(grep -nF '<!-- step:1d.5 — Brainstorm Panel -->' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
line_1d7=$(grep -nF '<!-- step:1d.7 — Design Outline (Outline-Approval Gate) -->' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
line_1e=$(grep -nF '<!-- step:1e — Discussion Mode Gate (Gate A) -->' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$line_1d5" && -n "$line_1d7" && -n "$line_1e" ]] || fail "(2974) missing Step 1d.5, 1d.7, or 1e anchor"
if (( line_1d5 >= line_1d7 || line_1d7 >= line_1e )); then
  fail "(2974) Step 1d.7 anchor must appear between Step 1d.5 and Step 1e"
fi
grep -Fq $'1d.7\toutline' "$REPO_ROOT/skills/design/scripts/step-name-registry.tsv" \
  || fail "(2974) step-name-registry.tsv missing 1d.7 outline row"
grep -Fq '> **🔶 /design 1d.7: outline**' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing outline banner"
grep -Fq '⏩ 1d.7: outline — skipped (already approved; .outline-approved present)' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing approved-sentinel skip breadcrumb"
# shellcheck disable=SC2016 # literal env var reference pinned in markdown
grep -Fq '$DESIGN_TMPDIR/.outline-approved' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing .outline-approved sentinel reference"
grep -Fq 'proceed to Step 2a' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing Step 2a skip handoff"
grep -Fq 'approved outline + existing plan; continue to Step 1e Gate A post-plan path' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing stale-sentinel post-plan recovery guard"
grep -Fq 'plan already exists; continue to Step 1e Gate A post-plan path even without .outline-approved' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing missing-sentinel post-plan recovery guard"
grep -Fq 'continue directly to **Step 1e Gate A**' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing explicit Step 1e successor for existing-plan skips"
# shellcheck disable=SC2016 # Markdown literal includes backticks and emoji intentionally.
grep -Fq 'print `✅ 1d.7: outline approved — proceeding to sketches`' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md missing outline-approve acknowledgment breadcrumb"
grep -Fq 'This sentinel is written **only** on explicit Approve.' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md must pin approve-only sentinel writes"
grep -Fq 'The already-planned ad-hoc Q&A-only branch does **not** invoke this file.' "$DESIGN_OUTLINE_MD" \
  || fail "(2974) design-outline.md must exclude ad-hoc Q&A-only runs from outline gating"
if grep -Fq 'proceed to Step 1e' "$DESIGN_OUTLINE_MD"; then
  fail "(2974) design-outline.md must not hand off outline approval to Step 1e"
fi
grep -Fq '1c→1d→1d.5→1d.7→2a→2a.5→2b→2b.5→3→3.5→3.6→3b→4→4b→5→5a→5b→5c.1→5c.5→5c.7→5c.8→6' "$SKILL_MD" \
  || fail "(2974) SKILL.md missing updated anti-halt sequence"
if grep -Fq '1c→1d→1d.5→1e' "$SKILL_MD"; then
  fail "(2974) SKILL.md still contains stale 1d.5→1e anti-halt sequence"
fi
grep -Fq '**Narrow exception — Step 1d.5 and Step 1d.7 only**' "$SKILL_MD" \
  || fail "(2974) SKILL.md missing Step 1d.5 and Step 1d.7 anti-halt exception"
grep -Fq 'Re-entry-only' "$APPROVAL_MD" \
  || fail "(2974) approval-gates.md Gate A must be re-entry-only"
grep -Fq 'design-outline.md' "$APPROVAL_MD" \
  || fail "(2974) approval-gates.md must cross-reference design-outline.md"
if grep -Fq 'first-time entry from Step 1d / Step 1d.5, proceed to Step 2a' "$APPROVAL_MD"; then
  fail "(2974) approval-gates.md still contains stale first-time Gate A proceed language"
fi
grep -Fq 'before entering Step **1d.7**' "$BRAINSTORM_MD" \
  || fail "(2974) brainstorm.md missing Step 1d.7 terminal handoff"
if grep -Fq 'before entering Step **1e**' "$BRAINSTORM_MD"; then
  fail "(2974) brainstorm.md still mentions Step 1e terminal handoff"
fi
grep -Fq 'Step 1d.5 (brainstorm panel, when enabled) or Step 1d.7 (outline) when brainstorm is off' "$DISCUSSION_MD" \
  || fail "(2974) discussion-rounds.md missing Step 1d.7 short-circuit/cap successor"
if grep -Fq 'proceed to Step 1e (Gate A)' "$DISCUSSION_MD"; then
  fail "(2974) discussion-rounds.md still routes Step 1d exits to Step 1e"
fi
grep -Fq 'cancelled-outline' "$REPO_ROOT/skills/design/scripts/render-final-summary.sh" \
  || fail "(2974) render-final-summary.sh missing cancelled-outline enum"
# shellcheck disable=SC2016 # Markdown enum literal in SKILL.md
grep -Fq 'cancelled-decompose` | `cancelled-outline` | `cancelled-plan-size-hard' "$SKILL_MD" \
  || fail "(2974) SKILL.md SUMMARY_OUTCOME enum missing cancelled-outline in documented order"
grep -Fq 'first-time entry handled by Step 1d.7; proceed to Step 2a' "$SKILL_MD" \
  || fail "(2974) SKILL.md missing Step 1e defensive entry guard"
grep -Fq 'outline not yet approved; return to Step 1d.7' "$SKILL_MD" \
  || fail "(2974) SKILL.md Step 1e must return pre-plan missing-outline flows to Step 1d.7"
# shellcheck disable=SC2016 # Markdown literal includes a literal env-var reference.
grep -Fq 'When `$DESIGN_TMPDIR/plan.txt` exists, stay on the post-plan gate path — never route back to Step 2a from Step 1e.' "$SKILL_MD" \
  || fail "(2974) SKILL.md Step 1e must not re-enter sketches once plan.txt exists"
# shellcheck disable=SC2016 # Markdown literal includes inline code formatting.
grep -Fq 'run the Gate A re-entry body even when `.outline-approved` is absent' "$SKILL_MD" \
  || fail "(2974) SKILL.md Step 1e must keep existing-plan paths on Gate A even without outline sentinel"
# shellcheck disable=SC2016 # Markdown literal includes a literal env-var reference.
grep -Fq 'exists, is non-empty, **and** `$DESIGN_TMPDIR/.outline-approved` exists' "$SKILL_MD" \
  || fail "(2974) SKILL.md must require .outline-approved for downstream outline consumption"
grep -Fq 'Step 1d sprawl returns to the pre-plan path that re-enters Step 1d.7 outline approval, not Gate A' "$SKILL_MD" \
  || fail "(2974) SKILL.md Step 2b.5 must route Step 1d sprawl back through Step 1d.7"
echo "PASS: (2974) Step 1d.7 outline approval anchors OK"

# Check 21 (#2930): Gate B auto-apply default and --manual opt-out pins.
grep -Fq '[--brainstorm] [--manual|-m] [--no-dedup]' "$SKILL_MD" \
  || fail "(2930) SKILL.md argument-hint missing [--manual|-m] between brainstorm and no-dedup"
contains "$PARSE_DESIGN_ARGV_SH" '--manual | -m)' '(FINDING_5) parse-design-argv.sh missing --manual|-m branch'
# shellcheck disable=SC2016 # Markdown table cell literal
grep -Fq '| `--manual` / `-m` |' "$SKILL_MD" \
  || fail "(2930) SKILL.md compact flag table missing --manual/-m row"
# shellcheck disable=SC2016 # SKILL.md bash excerpt; quotes are literal
grep -Fq -- '--manual-requested "$manual_requested"' "$SKILL_MD" \
  || fail "(2930) SKILL.md design-init-runparams invocation missing --manual-requested"
# shellcheck disable=SC2016 # Markdown literal; backticks are prose, not shell expansion.
if ! grep -Fq 'append `--manual-requested true` only when `manual_requested=true`' "$SKILL_MD" \
  && ! grep -Fq 'Append `--manual-requested true` on that follow-up invocation only when `manual_requested=true`' "$SKILL_MD"; then
  fail "(FINDING_16) SKILL.md must omit --manual-requested on non-manual runs"
fi
DESIGN_ROUTE_SH="$REPO_ROOT/skills/design/scripts/design-route.sh"
DESIGN_INIT_SH="$REPO_ROOT/skills/design/scripts/design-init-runparams.sh"
[[ -x "$DESIGN_ROUTE_SH" ]] || fail "design-route.sh must be executable"
[[ -x "$DESIGN_INIT_SH" ]] || fail "design-init-runparams.sh must be executable"
# shellcheck disable=SC2016 # jq filter literal
grep -Fq -- 'manual_gate_b = $merge_m' "$DESIGN_INIT_SH" \
  || fail "(FINDING_14) design-init-runparams.sh jq merge must overwrite manual_gate_b from current argv state"
# shellcheck disable=SC2016 # jq filter literal: $merge_p/$merge_b/$merge_m are jq vars, not shell vars.
grep -Fq -- '.partition_requested = (.partition_requested == true or $merge_p) | .brainstorm_requested = (.brainstorm_requested == true or $merge_b) | .manual_gate_b = $merge_m' "$DESIGN_INIT_SH" \
  || fail "(#3008) design-init-runparams.sh canonical Step 0b jq-merge filter must remain pinned for test-step0b-router-flag-recovery.sh"
grep -Fq 'append-tool-failure.sh' "$DESIGN_INIT_SH" \
  || fail "(FINDING_1) design-init-runparams.sh must call append-tool-failure.sh on jq-merge failure"
grep -Fq 'jq(router-flags-merge)' "$DESIGN_INIT_SH" \
  || fail "(FINDING_1) design-init-runparams.sh must pin jq(router-flags-merge) tool name"
grep -Fq 'larch-router-flags-merge' "$DESIGN_INIT_SH" \
  || fail "(FINDING_1) design-init-runparams.sh must use larch-router-flags-merge temp paths"
grep -Fq 'design Step 0b' "$DESIGN_INIT_SH" \
  || fail "(FINDING_1) design-init-runparams.sh must pin design Step 0b site for jq-merge failure"
grep -Fq 'refusing to recreate it with fallback defaults' "$DESIGN_INIT_SH" \
  || fail "(2930) design-init-runparams.sh fallback-missing path must refuse to recreate run-params with defaults"
grep -Fq 'partition, brainstorm, and/or manual requested but jq is unavailable' "$DESIGN_INIT_SH" \
  || fail "(2930) design-init-runparams.sh jq-unavailable warning missing manual"
grep -Fq -- '--manual-requested true' "$DESIGN_INIT_SH" \
  || fail "(FINDING_16) design-init-runparams.sh must support --manual-requested on manual runs"
# shellcheck disable=SC2016 # flags.md list marker uses backticks
grep -Fq '`--manual` / `-m`:' "$FLAGS_MD" \
  || fail "(2930) flags.md missing --manual/-m bullet anchor"
grep -Fq '### Apply-all body' "$APPROVAL_MD" \
  || fail "(2930) approval-gates.md missing Apply-all body heading"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'Execute `### Apply-all body` verbatim' "$APPROVAL_MD" \
  || fail "(2930) approval-gates.md missing Apply-all body references"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
apply_all_reference_count=$(grep -Fc 'Execute `### Apply-all body` verbatim' "$APPROVAL_MD")
[[ "$apply_all_reference_count" -ge 2 ]] \
  || fail "(2930) approval-gates.md must reference Apply-all body from both auto-apply and manual Apply all paths"
grep -Fq 'Determine Gate B mode only after the zero-findings short-circuit above proves there is at least one accepted in-scope finding to handle.' "$APPROVAL_MD" \
  || fail "(FINDING_1) approval-gates.md must resolve Gate B mode before mode-specific presentation"
zero_findings_line=$(grep -nF '### Zero-findings short-circuit' "$APPROVAL_MD" | head -1 | cut -d: -f1 || true)
mode_line=$(grep -nF '#### Gate B mode (auto-apply vs manual)' "$APPROVAL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$zero_findings_line" && -n "$mode_line" ]] \
  || fail "(FINDING_2) approval-gates.md must contain both zero-findings and Gate B mode headings"
if (( zero_findings_line >= mode_line )); then
  fail "(FINDING_2) approval-gates.md must place zero-findings before Gate B mode resolution"
fi
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'if sourced session env exports `MANUAL_REQUESTED=true`, set `manual_gate_b=true` immediately' "$APPROVAL_MD" \
  || fail "(FINDING_2) approval-gates.md missing MANUAL_REQUESTED session-env fallback"
# shellcheck disable=SC2016 # Markdown literal; jq program is prose, not command substitution
grep -Fq "jq -r '.manual_gate_b // false'" "$APPROVAL_MD" \
  || fail "(FINDING_9) approval-gates.md must pin jq -r '.manual_gate_b // false' for missing/null coercion"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'When `manual_gate_b=false` and `LOOP_STATUS` is neither `converged` nor `cap-hit`, execute the auto-apply path:' "$APPROVAL_MD" \
  || fail "(2930) approval-gates.md missing unique auto-apply mode branch anchor"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'When `manual_gate_b=true`, print a table under the header `## Plan Review Findings — Review`' "$APPROVAL_MD" \
  || fail "(2930) approval-gates.md missing manual mode presentation branch"
grep -Fq '## Plan Review Findings — Auto-applying' "$APPROVAL_MD" \
  || fail "(FINDING_7) approval-gates.md missing Gate B auto-apply header pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'let `manual_requested=true` force `manual_gate_b=true`' "$APPROVAL_MD" \
  || fail "(FINDING_13) approval-gates.md missing defensive in-memory manual_requested pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'defaulting to auto-apply unless a true-only manual override is already present' "$APPROVAL_MD" \
  || fail "(FINDING_1) approval-gates.md missing degraded-path auto-apply fallback pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'Session env and in-memory state are true-only overrides; persisted `run-params.json` remains the canonical source for proving `manual_gate_b=false`.' "$APPROVAL_MD" \
  || fail "(FINDING_12) approval-gates.md must pin the Gate B mode precedence chain"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'Do not run a separate rollback pass inside Gate B based on `discussion-round2.md`.' "$APPROVAL_MD" \
  || fail "(FINDING_13) approval-gates.md must forbid Gate B rollback from discussion-round2.md"
grep -Fq '### Shared post-apply pipeline' "$APPROVAL_MD" \
  || fail "(FINDING_3) approval-gates.md missing shared post-apply pipeline heading"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
grep -Fq 'then Execute `### Shared post-apply pipeline` verbatim' "$APPROVAL_MD" \
  || fail "(FINDING_19) approval-gates.md one-by-one path must call the shared post-apply pipeline verbatim"
# shellcheck disable=SC2016 # Markdown literal; backticks are approval-gates.md prose, not command substitution
shared_pipeline_reference_count=$(grep -Fc 'Execute `### Shared post-apply pipeline` verbatim' "$APPROVAL_MD")
[[ "$shared_pipeline_reference_count" -eq 2 ]] \
  || fail "(FINDING_20) approval-gates.md must reference the shared post-apply pipeline from exactly two Gate B call sites"

grep -Fq 'Gate B — Post-Review Chooser; the zero-findings short-circuit will pass straight through to Step 3b' "$PLAN_REVIEW_MD" \
  || fail "(FINDING_6) plan-review.md missing zero-findings Gate B forwarding pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are plan-review prose, not command substitution
grep -Fq 'findings are surfaced to Gate B, which applies them per `manual_gate_b` mode' "$PLAN_REVIEW_MD" \
  || fail "(FINDING_6) plan-review.md missing Gate B dual-mode application pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are SKILL.md prose, not command substitution
grep -Fq 'When Gate B resolves `manual_gate_b=false`, it auto-applies findings only on the `LOOP_STATUS=complete|revision-failed` branches; `LOOP_STATUS=converged|cap-hit` is passive-summary only because the loop already revised `plan.txt`, and `LOOP_STATUS=emit-plan-failed` routes through the warning/manual handling branch.' "$SKILL_MD" \
  || fail "(FINDING_7) SKILL.md Step 3 missing auto-apply pin"
# shellcheck disable=SC2016 # Markdown literal; backticks are SKILL.md prose, not command substitution
grep -Fq 'it first checks the zero-findings short-circuit, then resolves `manual_gate_b` before any mode-specific presentation' "$SKILL_MD" \
  || fail "(FINDING_7) SKILL.md Step 3.5 missing zero-findings-before-mode pin"
grep -Fq 'design-init-runparams.sh' "$SKILL_MD" \
  || fail "(FINDING_13) SKILL.md Step 0b must invoke design-init-runparams.sh"
grep -Fq 'write-design-current-env.sh' "$DESIGN_INIT_SH" \
  || fail "(FINDING_13) design-init-runparams.sh must call write-design-current-env.sh"
grep -Fq 'write-run-params.sh' "$DESIGN_INIT_SH" \
  || fail "(FINDING_13) design-init-runparams.sh must call write-run-params.sh"
grep -Fq 'tracking-issue-write.sh' "$DESIGN_INIT_SH" \
  || fail "(FINDING_13) design-init-runparams.sh must call tracking-issue-write.sh rename"
# shellcheck disable=SC2016 # grep literal contains shell variables and quotes intentionally
grep -Fq -- '--issue-number "$ISSUE"' "$DESIGN_INIT_SH" \
  || fail "(FINDING_13) design-init-runparams.sh current-design-env refresh must pass --issue-number"
# shellcheck disable=SC2016 # grep literal contains shell variables and quotes intentionally
grep -Fq -- '--claude-pid "$CLAUDE_PID"' "$DESIGN_INIT_SH" \
  || fail "(FINDING_13) design-init-runparams.sh current-design-env refresh must pass --claude-pid"
grep -Fq '_wdce_args+=(--manual-requested true)' "$DESIGN_INIT_SH" \
  || fail "(FINDING_13) design-init-runparams.sh must add --manual-requested only on manual runs"
grep -Fq 'INIT_STATUS=env-refresh-failed' "$DESIGN_INIT_SH" \
  || fail "(FINDING_20) design-init-runparams.sh must emit env-refresh-failed on write-design-current-env.sh failure"
grep -Fq 'write-design-current-env.sh failed during Step 0b env refresh' "$SKILL_MD" \
  || fail "(FINDING_20) SKILL.md missing dedicated env-refresh-failed operator banner"
init_refresh_line=$(grep -nF 'write-design-current-env.sh' "$DESIGN_INIT_SH" | head -1 | cut -d: -f1 || true)
init_rename_line=$(grep -nF 'tracking-issue-write.sh' "$DESIGN_INIT_SH" | head -1 | cut -d: -f1 || true)
init_run_params_line=$(grep -nF 'write-run-params.sh' "$DESIGN_INIT_SH" | head -1 | cut -d: -f1 || true)
[[ -n "$init_refresh_line" && -n "$init_rename_line" && -n "$init_run_params_line" ]] \
  || fail "(FINDING_13) could not locate design-init-runparams.sh env/rename/run-params lines"
if (( init_refresh_line >= init_rename_line || init_refresh_line >= init_run_params_line )); then
  fail "(FINDING_2) design-init-runparams.sh must refresh current-design-env before rename and write-run-params"
fi
grep -Fq 'design-route.sh configuration error (exit 2)' "$SKILL_MD" \
  || fail "(FINDING_3) SKILL.md Step 0b missing design-route.sh exit 2 abort prose"
grep -Fq 'design-init-runparams.sh configuration error (exit 2)' "$SKILL_MD" \
  || fail "(FINDING_3) SKILL.md Step 0b missing design-init-runparams.sh exit 2 abort prose"
# shellcheck disable=SC2016 # Markdown literal contains shell variables from the fenced SKILL.md snippet.
grep -Fq 'design-route.sh failed (exit ${_route_rc}); aborting /design' "$SKILL_MD" \
  || fail "(FINDING_9) SKILL.md Step 0b missing design-route.sh operational failure abort prose"
# shellcheck disable=SC2016 # Markdown literal contains shell variables from the fenced SKILL.md snippet.
grep -Fq 'design-init-runparams.sh failed (exit ${_init_rc}); aborting /design' "$SKILL_MD" \
  || fail "(FINDING_9) SKILL.md Step 0b missing design-init-runparams.sh operational failure abort prose"
# shellcheck disable=SC2016 # Markdown literal contains shell variables from the fenced SKILL.md snippet.
grep -Fq 'design-init-runparams.sh failed (INIT_STATUS=${INIT_STATUS:-unknown}); aborting /design' "$SKILL_MD" \
  || fail "(FINDING_9) SKILL.md Step 0b missing design-init-runparams.sh exit-1 status abort prose"
grep -Fq '_route_out=' "$SKILL_MD" \
  || fail "(FINDING_2) SKILL.md Step 0b missing _route_out capture"
grep -Fq '_init_out=' "$SKILL_MD" \
  || fail "(FINDING_2) SKILL.md Step 0b missing _init_out capture"
grep -Fq '.design-route-result.env' "$SKILL_MD" \
  || fail "(FINDING_2) SKILL.md Step 0b missing .design-route-result.env file-first read"
grep -Fq '.design-init-runparams-result.env' "$SKILL_MD" \
  || fail "(FINDING_2) SKILL.md Step 0b missing .design-init-runparams-result.env file-first read"
if grep -Fq 'phase_driver_read_result_env' "$SKILL_MD"; then
  step0b_block=$(awk '/^### 0b /,/^### Final summary block$/' "$SKILL_MD")
  if printf '%s\n' "$step0b_block" | grep -Fq 'phase_driver_read_result_env'; then
    fail "(FINDING_2) SKILL.md Step 0b must not call phase_driver_read_result_env"
  fi
fi
grep -Fq 'issue-body.txt' "$SKILL_MD" \
  || fail "(FINDING_1 R4) SKILL.md Step 0b must write issue-body.txt after fetch"
grep -Fq 'resolve-repo.sh' "$SKILL_MD" \
  || fail "(FINDING_1 R4) SKILL.md Step 0b must resolve REPO after fetch"
grep -Fq "\${REPO:+--repo \"\$REPO\"}" "$SKILL_MD" \
  || fail "(FINDING_1 R4) SKILL.md Step 0b must thread REPO on driver invocations"
grep -Fq 'design-pause-load.sh' "$DESIGN_ROUTE_SH" \
  || fail "(FINDING_1 R4) design-route.sh must invoke design-pause-load.sh"
grep -Fq "\${REPO:+--repo" "$DESIGN_ROUTE_SH" \
  || fail "(FINDING_1 R4) design-route.sh must thread REPO on design-pause-load.sh"
grep -Fq "\${REPO:+--repo" "$DESIGN_INIT_SH" \
  || fail "(FINDING_1 R4) design-init-runparams.sh must thread REPO on tracking-issue-write.sh rename"
grep -Fq 'MARK_START=' "$DESIGN_ROUTE_SH" \
  || fail "(FINDING_4) design-route.sh must pin MARK_START plan marker regex"
grep -Fq 'MARK_END=' "$DESIGN_ROUTE_SH" \
  || fail "(FINDING_4) design-route.sh must pin MARK_END plan marker regex"
step0b_block=$(awk '/^### 0b /,/^### Final summary block$/' "$SKILL_MD")
# shellcheck disable=SC2016 # Markdown literal contains shell variables from the fenced SKILL.md snippet.
printf '%s\n' "$step0b_block" | grep -Fq 'printf '\''%s\n'\'' "WARN=$_value"' \
  || fail "(FINDING_1 R5) SKILL.md Step 0b file-first route loop must immediately print WARN breadcrumbs"
# shellcheck disable=SC2016 # Markdown literal contains shell variables from the fenced SKILL.md snippet.
printf '%s\n' "$step0b_block" | grep -Fq 'printf '\''%s\n'\'' "ERROR=$_value"' \
  || fail "(FINDING_1 R5) SKILL.md Step 0b file-first route loop must immediately print ERROR breadcrumbs"
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
printf '%s\n' "$step0b_block" | grep -Fq 'On `LOAD_OK=false` fallthrough inside the driver, `WARN`/`ERROR` breadcrumbs were emitted above before `ROUTE` branches.' \
  || fail "(FINDING_10) SKILL.md Step 0b missing LOAD_OK=false fallthrough breadcrumb prose"
printf '%s\n' "$step0b_block" | grep -Fq '_route_warn_lines' \
  || fail "(FINDING_10) SKILL.md Step 0b missing route warning collection"
printf '%s\n' "$step0b_block" | grep -Fq '_route_error_lines' \
  || fail "(FINDING_10) SKILL.md Step 0b missing route error collection"
printf '%s\n' "$step0b_block" | grep -Fq 'MARKER_AGE=0' \
  || fail "(FINDING_7) SKILL.md Step 0b must default MARKER_AGE before reentry guard branch"
printf '%s\n' "$step0b_block" | grep -Fq 'MARKER_TTL=300' \
  || fail "(FINDING_7) SKILL.md Step 0b must default MARKER_TTL before reentry guard branch"
printf '%s\n' "$step0b_block" | grep -Fq '_wdce_resume_args' \
  || fail "(FINDING_9) SKILL.md Step 0b missing resume write-design-current-env args array"
# shellcheck disable=SC2016 # Markdown literal contains shell variables from the fenced SKILL.md snippet.
printf '%s\n' "$step0b_block" | grep -Fq '${REPO:+--repo "$REPO"}' \
  || fail "(FINDING_9) SKILL.md Step 0b resume env refresh must thread repo"
printf '%s\n' "$step0b_block" | grep -Fq '_wdce_resume_rc=$?' \
  || fail "(FINDING_18) SKILL.md Step 0b resume env refresh must capture rc"
printf '%s\n' "$step0b_block" | grep -Fq 'resume env refresh failed via write-design-current-env.sh' \
  || fail "(FINDING_18) SKILL.md Step 0b resume env refresh must handle failure"
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
printf '%s\n' "$step0b_block" | grep -Fq 'only when `ROUTE=proceed`' \
  || fail "(FINDING_15) SKILL.md Step 0b sub-step 6 must be ROUTE=proceed guarded"

skill_fetch_line=$(printf '%s\n' "$step0b_block" | grep -nF '2. **Fetch issue' | head -1 | cut -d: -f1 || true)
skill_route_line=$(printf '%s\n' "$step0b_block" | grep -nF '2.5. **Route driver**' | head -1 | cut -d: -f1 || true)
skill_clarify_line=$(printf '%s\n' "$step0b_block" | grep -nF '3. **Clarify loop**' | head -1 | cut -d: -f1 || true)
[[ -n "$skill_fetch_line" && -n "$skill_route_line" && -n "$skill_clarify_line" ]] \
  || fail "(FINDING_4) SKILL.md Step 0b missing fetch / route / clarify anchors"
if (( skill_fetch_line >= skill_route_line || skill_route_line >= skill_clarify_line )); then
  fail "(FINDING_4) SKILL.md Step 0b must fetch before route driver before clarify"
fi

route_resume_line=$(grep -nF '# 1. Resume detection' "$DESIGN_ROUTE_SH" | head -1 | cut -d: -f1 || true)
route_title_line=$(grep -nF '# 2. Title-eligibility' "$DESIGN_ROUTE_SH" | head -1 | cut -d: -f1 || true)
route_reentry_line=$(grep -nF '# 3. Re-entry guard' "$DESIGN_ROUTE_SH" | head -1 | cut -d: -f1 || true)
route_verdict_line=$(grep -nF '# 4. Verdict' "$DESIGN_ROUTE_SH" | head -1 | cut -d: -f1 || true)
[[ -n "$route_resume_line" && -n "$route_title_line" && -n "$route_reentry_line" && -n "$route_verdict_line" ]] \
  || fail "(FINDING_4) design-route.sh missing route phase comment anchors"
if (( route_resume_line >= route_title_line || route_title_line >= route_reentry_line || route_reentry_line >= route_verdict_line )); then
  fail "(FINDING_4) design-route.sh must run resume before title before re-entry before verdict"
fi
grep -Fq 'step_is_registered' "$DESIGN_ROUTE_SH" \
  || fail "(FINDING_14) design-route.sh must re-validate resume STEP against registry"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq 'design-pause-load.sh" --design-tmpdir "$DESIGN_TMPDIR" --issue "$ISSUE" ${REPO:+--repo "$REPO"})' "$DESIGN_ROUTE_SH" \
  || fail "(FINDING_14) design-route.sh must capture pause-load stdout only"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq 'phase_driver_write_result_env "$RESULT_ENV"' "$DESIGN_ROUTE_SH" \
  || fail "(FINDING_19) design-route.sh must write result env"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
write_env_line=$(grep -nF 'phase_driver_write_result_env "$RESULT_ENV"' "$DESIGN_ROUTE_SH" | head -1 | cut -d: -f1 || true)
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
emit_kv_line=$(grep -nF 'emit_kv "${kv%%=*}" "${kv#*=}"' "$DESIGN_ROUTE_SH" | head -1 | cut -d: -f1 || true)
[[ -n "$write_env_line" && -n "$emit_kv_line" ]] || fail "(FINDING_19) design-route.sh missing result-env write / stdout emit anchors"
if (( write_env_line >= emit_kv_line )); then
  fail "(FINDING_19) design-route.sh must write result env before stdout ROUTE emission"
fi
grep -Fq 'cancel-pause-load' "$SKILL_MD" \
  || fail "(FINDING_5) SKILL.md Step 0b missing cancel-pause-load orchestrator branch"
grep -Fq 'ROUTE=cancel-pause-load' "$DESIGN_ROUTE_SH" \
  || fail "(FINDING_5) design-route.sh must emit ROUTE=cancel-pause-load for invalid pause resume"
grep -Fq 'step-name-registry.tsv missing' "$DESIGN_ROUTE_SH" \
  || fail "(FINDING_8) design-route.sh must fail when step-name-registry.tsv is missing"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
init_write_env_line=$(grep -nF 'phase_driver_write_result_env "$RESULT_ENV" "${_init_kvs[@]}"' "$DESIGN_INIT_SH" | head -1 | cut -d: -f1 || true)
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
init_emit_status_line=$(grep -nF 'emit_kv INIT_STATUS "$INIT_STATUS"' "$DESIGN_INIT_SH" | tail -1 | cut -d: -f1 || true)
[[ -n "$init_write_env_line" && -n "$init_emit_status_line" ]] \
  || fail "(FINDING_36) design-init-runparams.sh missing success-path result-env write / stdout emit anchors"
if (( init_write_env_line >= init_emit_status_line )); then
  fail "(FINDING_36) design-init-runparams.sh must write result env before stdout INIT_STATUS emission"
fi
grep -Fq 'missing or invalid ROUTE after design-route.sh' "$SKILL_MD" \
  || fail "(FINDING_19) SKILL.md Step 0b missing ROUTE validation after design-route handoff"
grep -Fq 'exited 0 without INIT_STATUS=ok and run-params.json' "$SKILL_MD" \
  || fail "(FINDING_20) SKILL.md Step 0b missing init success-path validation"
grep -Fq 'continuing with run-params write' "$DESIGN_INIT_SH" \
  || fail "(FINDING_21) design-init-runparams.sh missing best-effort rename warn+continue"
grep -Fq 'Partial-state retry' "$REPO_ROOT/skills/design/scripts/design-init-runparams.md" \
  || fail "(FINDING_21) design-init-runparams.md missing partial-state retry contract"

# Check FINDING_2678 (#2678): YES↔EXONERATE canonical anchor phrase pinned in plan-review.md + renderer.
CANONICAL_PHRASE='When in doubt between YES and EXONERATE, prefer EXONERATE'
RENDER_VOTER_SH="$REPO_ROOT/skills/shared/scripts/render-voter-prompt.sh"

voter1_line=$(grep -n '^- \*\*Voter 1\*\*' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$voter1_line" ]] || fail "(FINDING_2678) plan-review.md missing '- **Voter 1**' prompt anchor"
voter1_text=$(sed -n "${voter1_line}p" "$PLAN_REVIEW_MD")
grep -Fq "$CANONICAL_PHRASE" <<< "$voter1_text" \
  || fail "(FINDING_2678) plan-review.md Voter 1 prompt missing canonical phrase: $CANONICAL_PHRASE"

shared_line=$(grep -n '^For Codex, Cursor, and their Claude replacement voters' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$shared_line" ]] || fail "(FINDING_2678) plan-review.md missing shared-voter-prompt anchor"
shared_text=$(sed -n "${shared_line}p" "$PLAN_REVIEW_MD")
grep -Fq "$CANONICAL_PHRASE" <<< "$shared_text" \
  || fail "(FINDING_2678) plan-review.md shared Voter 2/3 prompt missing canonical phrase: $CANONICAL_PHRASE"

grep -Fq "$CANONICAL_PHRASE" "$RENDER_VOTER_SH" \
  || fail "(FINDING_2678) render-voter-prompt.sh missing canonical phrase: $CANONICAL_PHRASE"

echo "PASS: FINDING_2678 — YES↔EXONERATE canonical anchor phrase OK (plan-review.md + renderer)"

# Check 19 (#2672): decomposition panel replaces Split-path stub.
DECOMP_REF="$REPO_ROOT/skills/design/references/decompose-panel.md"
[[ -f "$DECOMP_REF" ]] || fail "(19) references/decompose-panel.md missing"
grep -Fq 'decompose-panel-dispatch.sh' "$DECOMP_REF" \
  || fail "(19) decompose-panel.md must retain decompose-panel-dispatch.sh anchor for structure tests"
grep -Fq 'decompose-panel-dispatch.sh' "$SKILL_MD" \
  || fail "(19) SKILL.md Split-path must reference decompose-panel-dispatch.sh"
! grep -q 'decomposition panel is in development' "$SKILL_MD" \
  || fail "(19) SKILL.md must not retain the pre-panel stub string"
echo "PASS: (19) decomposition panel Split-path anchors OK"

# Check 18 (#2702): literal plan-preview header anchors in Step 3 + Gate C prose.
step3_block=$(awk '/^<!-- step:3 /,/^<!-- step:3.5 /' "$SKILL_MD")
printf '%s\n' "$step3_block" | grep -Fq '## Plan Candidate for Review' \
  || fail "(18) SKILL.md Step 3 block missing ## Plan Candidate for Review anchor"
gate_c_block=$(awk '/^## Gate C/,/^## State invariants/' "$APPROVAL_MD")
printf '%s\n' "$gate_c_block" | grep -Fq '## Final Design Plan' \
  || fail "(18) approval-gates.md Gate C block missing ## Final Design Plan anchor"
# Check 20 (#2800): Step 0b title-eligibility filter anchors (extracted to design-route.sh).
grep -Fq 'title_has_lifecycle_reject_prefix' "$DESIGN_ROUTE_SH" \
  || fail "(20) design-route.sh missing title_has_lifecycle_reject_prefix"
grep -Fq 'title_has_archival_report_prefix' "$DESIGN_ROUTE_SH" \
  || fail "(20) design-route.sh missing title_has_archival_report_prefix"
grep -Fq 'title_starts_with_brainstorm' "$DESIGN_ROUTE_SH" \
  || fail "(20) design-route.sh missing title_starts_with_brainstorm"
grep -Fq 'cancelled-title-filter' "$SKILL_MD" \
  || fail "(20) SKILL.md missing cancelled-title-filter enum"
grep -Fq 'issue title starts with managed lifecycle marker' "$SKILL_MD" \
  || fail "(20) SKILL.md missing lifecycle-reject banner text"
grep -Fq 'issue title matches archival report-prefix' "$SKILL_MD" \
  || fail "(20) SKILL.md missing archival-report-reject banner text"
grep -Fq 'detected Brainstorm title prefix — auto-enabling brainstorm mode' "$SKILL_MD" \
  || fail "(20) SKILL.md missing brainstorm info banner text"
title_cancel_line=$(grep -n 'cancel-title-filter' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
clarify_line=$(grep -n '^3\. \*\*Clarify loop\*\*' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$title_cancel_line" && -n "$clarify_line" ]] \
  || fail "(20) Step 0b cancel-title-filter / clarify anchors missing"
if (( title_cancel_line >= clarify_line )); then
  fail "(20) Step 0b orchestrator must handle cancel-title-filter before clarify branch"
fi
echo "PASS: (20) Step 0b title-eligibility filter anchors OK"

# Check 21 (#2959): pause/resume prelude and completion sentinels.
assert_bash_fences_have_pause_check() {
  local missing
  missing=$(awk '
    /<!-- step:1c/ { start=1; in_fence=0 }
    start && /^```bash$/ { in_fence=1; saw_source=0; saw_pause=0; next }
    start && in_fence && /^```$/ {
      if (saw_source && !saw_pause) print source_line
      in_fence=0
      next
    }
    start && in_fence && /current-design-env-\$PPID\.sh/ {
      saw_source=1
      source_line=NR
      next
    }
    start && in_fence && saw_source && /design-pause-save\.sh/ { saw_pause=1 }
  ' "$SKILL_MD")
  [[ -z "$missing" ]] || fail "(21) current-design-env source lines missing pause-check after lines: $missing"
}

assert_step_completion_sentinels() {
  local step start_pat end_pat start_line end_line section
  for step in 0c 1c 1d 1d.5 1e 2a 2a.5 2b 2b.5 3 3.5 3.6 3b 4 4b 5b 5c 5d 6; do
    case "$step" in
      0c) start_pat='### 0c —'; end_pat='<!-- step:1c' ;;
      1c) start_pat='<!-- step:1c'; end_pat='<!-- step:1d' ;;
      1d) start_pat='<!-- step:1d —'; end_pat='<!-- step:1d.5' ;;
      1d.5) start_pat='<!-- step:1d.5'; end_pat='<!-- step:1e' ;;
      1e) start_pat='<!-- step:1e'; end_pat='<!-- step:2a' ;;
      2a) start_pat='<!-- step:2a —'; end_pat='### 2a.5' ;;
      2a.5) start_pat='### 2a.5'; end_pat='<!-- step:2b' ;;
      2b) start_pat='<!-- step:2b —'; end_pat='### Step 2b.5' ;;
      2b.5) start_pat='### Step 2b.5'; end_pat='<!-- step:3' ;;
      3) start_pat='<!-- step:3 —'; end_pat='<!-- step:3.5' ;;
      3.5) start_pat='<!-- step:3.5'; end_pat='<!-- step:3.6' ;;
      3.6) start_pat='<!-- step:3.6'; end_pat='<!-- step:3b' ;;
      3b) start_pat='<!-- step:3b'; end_pat='<!-- step:4 —' ;;
      4) start_pat='<!-- step:4 —'; end_pat='<!-- step:4b' ;;
      4b) start_pat='<!-- step:4b'; end_pat='### 5b' ;;
      5b) start_pat='### 5b'; end_pat='### 5c' ;;
      5c) start_pat='### 5c'; end_pat='### 5d' ;;
      5d) start_pat='### 5d'; end_pat='<!-- step:6' ;;
      6) start_pat='<!-- step:6'; end_pat='' ;;
    esac
    start_line=$(grep -nF "$start_pat" "$SKILL_MD" | head -1 | cut -d: -f1 || true)
    [[ -n "$start_line" ]] || fail "(21) SKILL.md missing start anchor for step $step"
    if [[ -n "$end_pat" ]]; then
      end_line=$(grep -nF "$end_pat" "$SKILL_MD" | head -1 | cut -d: -f1 || true)
      [[ -n "$end_line" ]] || fail "(21) SKILL.md missing end anchor for step $step"
      section=$(sed -n "${start_line},$((end_line - 1))p" "$SKILL_MD")
    else
      section=$(sed -n "${start_line},\$p" "$SKILL_MD")
    fi
    printf '%s\n' "$section" | grep -Fq ".completed/step-$step" \
      || fail "(21) SKILL.md missing step-local .completed sentinel for step $step"
  done
}

assert_bash_fences_have_pause_check
assert_step_completion_sentinels
grep -Fq 'design-route.sh' "$SKILL_MD" \
  || fail "(21) SKILL.md missing design-route.sh invocation"
grep -Fq 'design-pause-load.sh' "$DESIGN_ROUTE_SH" \
  || fail "(21) design-route.sh missing design-pause-load.sh invocation"
grep -Fq 'write-design-current-env.sh' "$SKILL_MD" \
  || fail "(21) SKILL.md missing resume env refresh via write-design-current-env.sh"
grep -Fq 'write-design-current-env.sh' "$DESIGN_INIT_SH" \
  || fail "(21) design-init-runparams.sh must refresh env before rename (single refresh)"
echo "PASS: (21) /design pause/resume structure anchors OK"

# Checks 24-26 (#2935): /design same-session re-entry guard pins.
grep -Fq 'title_has_lifecycle_reject_prefix' "$DESIGN_ROUTE_SH" \
  || fail "(24) design-route.sh missing title_has_lifecycle_reject_prefix"
grep -Fq 'design_reentry_marker_hit' "$DESIGN_ROUTE_SH" \
  || fail "(24) design-route.sh missing design_reentry_marker_hit"
step0b_reentry_order=$(awk '
  /^### 0b / { in0b=1; next }
  /^### Final summary block$/ && in0b { in0b=0 }
  in0b && /cancel-title-filter/ && !title { title=NR }
  in0b && /cancel-reentry-guard/ && !guard { guard=NR }
  in0b && /^3\. \*\*Clarify loop\*\*/ && !clarify { clarify=NR }
  END {
    if (!title || !guard || !clarify) exit 2
    if (!(title < guard && guard < clarify)) exit 1
  }
' "$SKILL_MD" || echo "$?")
case "${step0b_reentry_order:-0}" in
  0) ;;
  1|2) fail "(24) SKILL.md missing cancel-title-filter / cancel-reentry-guard orchestrator branches OR clarify ordering regression" ;;
  *) fail "(24) unexpected Step 0b re-entry guard ordering check exit: ${step0b_reentry_order:-?}" ;;
esac

publish_marker_line=$(grep -nF 'design_reentry_marker_write' "$DESIGN_PUBLISH_SH" | head -1 | cut -d: -f1 || true)
publish_rename_line=$(grep -n 'tracking-issue-write.sh' "$DESIGN_PUBLISH_SH" | grep 'state designed' | head -1 | cut -d: -f1 || true)
[[ -n "$publish_marker_line" && -n "$publish_rename_line" && "$publish_marker_line" -lt "$publish_rename_line" ]] \
  || fail "(25) design-publish.sh design_reentry_marker_write must precede tracking-issue-write.sh rename --state designed"
[[ -n "$publish_marker_line" && -n "$publish_log_line" && "$publish_marker_line" -lt "$publish_log_line" ]] \
  || fail "(25) design-publish.sh design_reentry_marker_write must precede design-log-publish.sh"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq '${REPO:+--repo' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must forward REPO via \${REPO:+--repo}"
grep -Fq 'design-publish.sh' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c must invoke design-publish.sh"
grep -Fq '.design-publish-result.env' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c must read .design-publish-result.env file-first"
grep -Fq 'design-publish.sh configuration error (exit 2)' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing design-publish.sh exit 2 abort prose"
grep -Fq '.completed/step-5c' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c must write .completed/step-5c sentinel"
# shellcheck disable=SC2016 # Markdown literal contains $DESIGN_TMPDIR and backticks intentionally.
grep -Fq ': > "$DESIGN_TMPDIR/.completed/step-5c"` **only when** `PLAN_WRITE_OK=true`' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c must gate step-5c sentinel on PLAN_WRITE_OK=true"
grep -Fq 'result-env write failed (exit 3)' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing design-publish.sh exit 3 result-env WARN prose"
grep -Fq '_publish_rc` is 0, 1, or 3' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing exit 3 parse-and-continue contract"
grep -Fq '_publish_rc`=3' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing _publish_rc=3 contract"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq 'if ! "$PLUGIN_ROOT/scripts/plan-block-write.sh"' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must use if ! around plan-block-write.sh"
grep -Fq 'export ISSUE_NUMBER' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must export ISSUE_NUMBER before render-final-summary.sh"
grep -Fq 'export SESSION_ID' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must export SESSION_ID before render-final-summary.sh"
grep -Fq 'render-final-summary.sh' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must invoke render-final-summary.sh"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq 'phase_driver_write_result_env "$RESULT_ENV"' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must write result env via phase_driver_write_result_env"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq '_publish_out=$("$PLUGIN_ROOT/scripts/design-log-publish.sh"' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must subshell-capture design-log-publish.sh stdout"
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
grep -Fq '_upsert_out=$("$PLUGIN_ROOT/scripts/upsert-diagrams-comment.sh"' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must subshell-capture upsert-diagrams-comment.sh stdout"
grep -Fq '.completed/step-5b' "$DESIGN_PUBLISH_SH" \
  || fail "(15b) design-publish.sh must require .completed/step-5b precondition"
grep -Fq 'exit 1 is the normal plan-block-write failure path' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing exit 1 parse-then-branch contract"
grep -Fq '_publish_rc` ∈ {0, 1, 3}' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c missing driver exit-code contract for rc 0, 1, or 3"
# shellcheck disable=SC2016
grep -Fq 'do not abort solely because `_publish_rc`=1' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c must not abort solely on driver exit 1"
# shellcheck disable=SC2016
grep -Fq '"${_publish_rc:-0}" -ne 3' "$SKILL_MD" \
  || fail "(15b) SKILL.md Step 5c unexpected-rc guard must exclude exit 3"

grep -Fq '**⚠ /design: refusing spurious re-entry — guard=session-cache' "$SKILL_MD" \
  || fail "(26) SKILL.md missing literal session-cache banner"
if ! grep -Fq 'delete <DESIGN_REENTRY_MARKER_PATH> to override.' "$SKILL_MD" \
  && ! grep -Fq "delete \${DESIGN_REENTRY_MARKER_PATH} to override." "$SKILL_MD"; then
  fail "(26) SKILL.md must document DESIGN_REENTRY_MARKER_PATH in the session-cache banner literal"
fi
echo "PASS: (24-26) Step 0b/5c re-entry guard anchors OK"

# Check FINDING_2667 (#2667): Gate B severity precedence prose in approval-gates.md.
contains "$APPROVAL_MD" 'important → High' '(FINDING_2667) approval-gates.md missing important → High mapping'
contains "$APPROVAL_MD" 'latent → Medium' '(FINDING_2667) approval-gates.md missing latent → Medium mapping'
contains "$APPROVAL_MD" 'nit → Low' '(FINDING_2667) approval-gates.md missing nit → Low mapping'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'When **any** accepted finding lacks that structured `- **Severity**:` line' \
  '(FINDING_2667) approval-gates.md missing all-or-nothing Concern-text fallback when structured Severity absent'
echo "PASS: FINDING_2667 — Gate B severity precedence prose OK"

# Check FINDING_2667_TEMPLATE (#2667): Accepted FINDING_N template field labels in plan-review.md.
finding_template_start=$(grep -n '^### Accepted FINDING_N template' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
finding_template_end=$(grep -n '^### Accepted OOS format' "$PLAN_REVIEW_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$finding_template_start" && -n "$finding_template_end" && "$finding_template_end" -gt "$finding_template_start" ]] \
  || fail "(FINDING_2667_TEMPLATE) could not locate FINDING_N template block in plan-review.md"
finding_template_block=$(sed -n "${finding_template_start},${finding_template_end}p" "$PLAN_REVIEW_MD")
for _label in \
  '- **Reviewer(s)**:' \
  '- **Severity**:' \
  '- **Focus area**:' \
  '- **Location**:' \
  '- **Concern**:' \
  '- **Proposed resolution**:'; do
  grep -Fq -- "$_label" <<< "$finding_template_block" \
    || fail "(FINDING_2667_TEMPLATE) plan-review.md FINDING_N template missing label: $_label"
done
echo "PASS: FINDING_2667_TEMPLATE — FINDING_N template six-field label set OK"

contains "$DESIGN_POSTPLAN_EMIT_SH" 'snapshot-plan-round.sh' 'design-postplan-emit.sh missing snapshot-plan-round'
contains "$DESIGN_POSTPLAN_EMIT_SH" 'write-original --design-tmpdir' 'design-postplan-emit.sh missing write-original invocation'
contains "$SKILL_MD" 'assess-plan-round.sh' 'SKILL.md Step 3.6 missing assess-plan-round.sh'
contains "$SKILL_MD" 'plan-review-round-cursor.txt' 'SKILL.md missing plan-review-round-cursor reference'
contains "$DESIGN_PLAN_QUALITY_ASSESSOR_SH" 'write-cursor --design-tmpdir' 'design-plan-quality-assessor.sh missing round-cursor advancement write-cursor'
contains "$DESIGN_PLAN_QUALITY_ASSESSOR_SH" 'assess-plan-round.sh' 'design-plan-quality-assessor.sh missing assess-plan-round'
contains "$DESIGN_PLAN_QUALITY_ASSESSOR_SH" 'snapshot-plan-round.sh' 'design-plan-quality-assessor.sh missing snapshot-plan-round'
# shellcheck disable=SC2016 # SKILL.md bash excerpt; qualified path must remain unexpanded.
contains "$SKILL_MD" '"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-plan-quality-assessor.sh"' 'SKILL.md missing qualified design-plan-quality-assessor invocation'
contains "$SKILL_MD" 'Step 3.6: refusing symlink .step3.6-assessor.env; using stdout fallback.' 'SKILL.md missing Step 3.6 symlink refusal'
contains "$SKILL_MD" 'design-plan-quality-assessor.sh configuration error (exit 2)' 'SKILL.md missing assessor exit-2 abort prose'
contains "$SKILL_MD" 'design-plan-quality-assessor.sh result env missing/unreadable and stdout did not populate mandatory keys; aborting /design.' 'SKILL.md missing assessor mandatory-keys abort prose'
contains "$MAKEFILE" 'test-design-plan-quality-assessor' 'Makefile missing test-design-plan-quality-assessor target'
[[ -x "$DESIGN_PLAN_QUALITY_ASSESSOR_SH" ]] || fail "design-plan-quality-assessor.sh must be executable"
contains "$DESIGN_PLAN_QUALITY_ASSESSOR_SH" 'LARCH_SNAPSHOT_PLAN_ROUND_SH' 'design-plan-quality-assessor.sh missing SNAPSHOT_SH seam'
contains "$DESIGN_PLAN_QUALITY_ASSESSOR_SH" 'LARCH_ASSESS_PLAN_ROUND_SH' 'design-plan-quality-assessor.sh missing ASSESS_SH seam'
contains "$DESIGN_PLAN_QUALITY_ASSESSOR_SH" '_write_result_and_emit' 'design-plan-quality-assessor.sh missing result flush helper'
contains "$DESIGN_PLAN_QUALITY_ASSESSOR_SH" '_assessor_pause_checkpoint' 'design-plan-quality-assessor.sh missing pause checkpoint'
contains "$DESIGN_PLAN_QUALITY_ASSESSOR_SH" 'set +e' 'design-plan-quality-assessor.sh missing child set +e capture'
# shellcheck disable=SC2016 # Script literal intentionally checks unexpanded parameter syntax.
contains "$RUN_STEP3_SH" '--round-num "$ROUND_NUM"' 'run-step3-review.sh missing --round-num ROUND_NUM to plan-review-loop'
contains "$SKILL_MD" 'Step 3.6' 'SKILL.md missing Step 3.6 section'
contains "$SKILL_MD" 'passive-summary auto-continue, auto-apply, Apply all, or full one-by-one without abort' 'SKILL.md missing passive-summary Step 3.6 settle path'
contains "$SKILL_MD" 'Passive-summary auto-continue routes through Step 3.6 before Step 3b' 'SKILL.md missing passive-summary auto-continue Step 3.6 routing pin'
# shellcheck disable=SC2016 # backticks and $ tokens are literal markdown pins
contains "$APPROVAL_MD" 'refresh the active Step 3 result state (including `.step3-plan-review-result.env`) before continuing to Gate B as complete-equivalent' 'approval-gates.md missing MainAgent re-tally Step 3 state refresh pin'
# shellcheck disable=SC2016 # backticks and $ tokens are literal markdown pins
contains "$SKILL_MD" 'Gate-B-bypass short-circuits (`LOOP_STATUS=cap-reached`, `TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached`, `tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, or `panel-failed`) bypass Step 3.5 **and Step 3.6** and continue to Step 3b instead' 'SKILL.md missing full Gate-B-bypass short-circuit list in Step 3.5 entry'
contains "$APPROVAL_MD" 'Passive-summary auto-continue routes through Step 3.6 before Step 3b' 'approval-gates.md missing passive-summary auto-continue Step 3.6 routing pin'
# shellcheck disable=SC2016 # backticks are literal markdown pins
contains "$APPROVAL_MD" 'Gate-B-bypass short-circuits (`LOOP_STATUS=cap-reached`, `TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached`, `tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, `panel-failed`) bypass Step 3.5 and Step 3.6 before Step 3b' 'approval-gates.md missing Gate-B-bypass Step 3.5/3.6 coverage pin'
# shellcheck disable=SC2016 # backticks and $ tokens are literal markdown pins
contains "$SKILL_MD" 'set `TALLY_PLAN_REVIEW_STATUS=ok`, `LOOP_STATUS=complete`, and persist both `.step3-plan-review-result.env` and `.step3-review-result.env` from the re-tally so Gate B and later Step 3 logic do not read stale 0-judge fallback state' 'SKILL.md missing MainAgent re-tally state refresh pin'
# shellcheck disable=SC2016 # $ tokens are literal markdown pins
contains "$SKILL_MD" '--findings-classification-out "$DESIGN_TMPDIR/plan-review/round-${ROUNDS_COMPLETED:-$ROUND_NUM}/findings-classification.tsv"' 'SKILL.md missing MainAgent re-tally findings-classification-out pin'
# shellcheck disable=SC2016 # backticks are literal markdown pins
contains "$APPROVAL_MD" 'Step 3 bypasses such as `LOOP_STATUS=cap-reached`, `tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, and `panel-failed` skip Gate B (and therefore Step 3.6) but still continue Step 3b → Step 4 → Step 4b with the current plan and artifacts.' 'approval-gates.md missing Gate C panel-failed bypass routing pin'
# shellcheck disable=SC2016 # backticks are literal markdown pins
for _bypass_line in \
  "$(grep -F 'Gate-B-bypass short-circuits (' "$SKILL_MD")" \
  "$(grep -F 'Gate-B-bypass short-circuits (' "$APPROVAL_MD")" \
  "$(grep -F 'When `LOOP_STATUS` is `tally-error`' "$APPROVAL_MD")" \
  "$(grep -F 'Step 3 bypasses such as `LOOP_STATUS=cap-reached`' "$APPROVAL_MD")" \
  "$(grep -F 'If `LOOP_STATUS` is `tally-error`' "$SKILL_MD")"
do
  [[ "$_bypass_line" != *'main-agent-vote-required'* ]] || fail 'bypass prose must not include main-agent-vote-required'
  [[ "$_bypass_line" != *'zero-findings-degraded-panel'* ]] || fail 'bypass prose must not include zero-findings-degraded-panel'
done
for _skip_breadcrumb in \
  '⏩ 3.6: assessor — skipped (Step 3 tally-error short-circuit)' \
  '⏩ 3.6: assessor — skipped (Step 3 degraded-empty-collector short-circuit)' \
  '⏩ 3.6: assessor — skipped (Step 3 panel-failed short-circuit)' \
  '⏩ 3.6: assessor — skipped (Step 3 cap-reached short-circuit)' \
  '⏩ 3.6: assessor — skipped (Step 3 plan-size-trigger short-circuit)' \
  '⏩ 3.6: assessor — skipped (Step 3 plan-validator-defects short-circuit)'
do
  contains "$SKILL_MD" "$_skip_breadcrumb" "SKILL.md missing Step 3.6 skip breadcrumb: $_skip_breadcrumb"
  contains "$APPROVAL_MD" "$_skip_breadcrumb" "approval-gates.md missing Step 3.6 skip breadcrumb: $_skip_breadcrumb"
done
contains "$SKILL_MD" 'cancelled-assessor-worse' 'SKILL.md missing cancelled-assessor-worse outcome'
contains "$REPO_ROOT/skills/design/scripts/render-final-summary.sh" 'cancelled-assessor-worse' 'render-final-summary.sh missing cancelled-assessor-worse outcome'
contains "$REPO_ROOT/skills/design/scripts/test-render-final-summary.sh" "pass 'cancelled-assessor-worse outcome'" 'test-render-final-summary.sh missing cancelled-assessor-worse harness pin'
contains "$REPO_ROOT/scripts/lib-timing-kinds.sh" 'claude-plan-assessor' 'lib-timing-kinds.sh missing claude-plan-assessor'
contains "$REPO_ROOT/scripts/lib-timing-kinds.sh" 'claude-phase2-plan-assessor' 'lib-timing-kinds.sh missing claude-phase2-plan-assessor'
contains "$REPO_ROOT/scripts/lib-timing-kinds.sh" 'claude-phase3-plan-assessor' 'lib-timing-kinds.sh missing claude-phase3-plan-assessor'
contains "$REPO_ROOT/scripts/lib-timing-kinds.sh" 'codex-plan-assessor' 'lib-timing-kinds.sh missing codex-plan-assessor'
contains "$REPO_ROOT/scripts/lib-timing-kinds.sh" 'codex-phase1-plan-assessor' 'lib-timing-kinds.sh missing codex-phase1-plan-assessor'
contains "$REPO_ROOT/scripts/lib-timing-kinds.sh" 'codex-phase2-plan-assessor' 'lib-timing-kinds.sh missing codex-phase2-plan-assessor'
contains "$REPO_ROOT/scripts/lib-timing-kinds.sh" 'cursor-plan-assessor' 'lib-timing-kinds.sh missing cursor-plan-assessor'
contains "$REPO_ROOT/scripts/lib-timing-kinds.sh" 'cursor-phase2-plan-assessor' 'lib-timing-kinds.sh missing cursor-phase2-plan-assessor'
contains "$REPO_ROOT/scripts/lib-timing-kinds.sh" 'cursor-phase3-plan-assessor' 'lib-timing-kinds.sh missing cursor-phase3-plan-assessor'
contains "$MAKEFILE" 'test-snapshot-plan-round' 'Makefile missing test-snapshot-plan-round'
contains "$MAKEFILE" 'test-dispatch-plan-assessors' 'Makefile missing test-dispatch-plan-assessors'
contains "$MAKEFILE" 'test-render-assessor-prompt' 'Makefile missing test-render-assessor-prompt'
contains "$MAKEFILE" 'test-tally-plan-assessor' 'Makefile missing test-tally-plan-assessor'
contains "$MAKEFILE" 'test-assess-plan-round' 'Makefile missing test-assess-plan-round'

echo "PASS: test-design-structure.sh — structural invariants hold (including security OOS exclusions)"
exit 0
