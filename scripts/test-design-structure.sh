#!/usr/bin/env bash
# Structural regression guard for the /design two-tier contract.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SKILL_MD="$REPO_ROOT/skills/design/SKILL.md"
FLAGS_MD="$REPO_ROOT/skills/design/references/flags.md"
APPROVAL_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
PLAN_REVIEW_MD="$REPO_ROOT/skills/design/references/plan-review.md"
DISCUSSION_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
PLAN_LOOP_SH="$REPO_ROOT/skills/design/scripts/plan-review-loop.sh"
PLAN_REVIEW_LOOP_SH="$PLAN_LOOP_SH"
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

contains "$SKILL_MD" '[--simple|--hard]' 'SKILL argument hint must expose only SIMPLE/HARD tiers'
contains "$SKILL_MD" '--trivial flag removed; tier consolidation in #2956. Use --simple or --hard.' 'SKILL missing removed --trivial hard-error prose'
contains "$SKILL_MD" 'design_classification == SIMPLE' 'SKILL missing SIMPLE branch prose'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'unless `design_classification == SIMPLE`, where the user-confirmed no-sketch carve-out applies' 'SKILL missing SIMPLE Design Mindset carve-out'
contains "$SKILL_MD" 'NO_SKETCHES_CLASSIFIED_SIMPLE' 'SKILL missing SIMPLE sketch sentinel'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'Skip sketches only when `design_classification == SIMPLE`' 'SKILL missing Anti-pattern #1 SIMPLE carve-out prose'
contains "$SKILL_MD" 'This is a SIMPLE-tier design. Bias the plan toward the **smallest change that achieves the goal**.' 'SKILL missing SIMPLE designer emphasis'
contains "$SKILL_MD" 'This is a HARD-tier design. Bias the plan toward **thoroughness**.' 'SKILL missing HARD designer emphasis'
contains "$SKILL_MD" 'review-round-count.txt' 'SKILL missing review-round counter'
# shellcheck disable=SC2016 # Markdown literal intentionally checks unexpanded parameter syntax.
contains "$SKILL_MD" '--round-cap "${LARCH_DESIGN_ROUND_CAP:-5}"' 'SKILL must pass explicit round-cap to plan-review-loop'
# shellcheck disable=SC2016 # Markdown literal intentionally checks unexpanded parameter syntax.
contains "$SKILL_MD" '--convergence-threshold "${LARCH_DESIGN_CONVERGENCE_THRESHOLD:-3}"' 'SKILL must pass convergence-threshold to plan-review-loop'
contains "$SKILL_MD" '.step3-plan-review-result.env' 'SKILL must source step3 plan-review result env'
contains "$SKILL_MD" 'result env is a symlink; ignoring it and using stdout fallback only' 'SKILL missing symlink-safe step3 result env warning'
contains "$SKILL_MD" 'invoke-plan-validator.sh' 'SKILL missing renamed validator helper'
contains "$SKILL_MD" 'read-design-classification.sh' 'SKILL missing classification reader'
contains "$SKILL_MD" '.step3-review-cap.env' 'SKILL missing persisted Step 3 cap state file'
contains "$SKILL_MD" 'STEP3_REVIEW_CAP_REACHED=false' 'SKILL missing persisted cap-false state'
contains "$SKILL_MD" 'STEP3_REVIEW_ROUND_NUM=' 'SKILL missing persisted Step 3 round number state'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'including `LOOP_STATUS=panel-failed`' 'SKILL missing panel-failed counter-consumption contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" 'MUST NOT persist when `TALLY_PLAN_REVIEW_STATUS=tally-error`' 'SKILL missing tally-error counter-skip contract'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" '`LOOP_STATUS=converged|cap-hit` — proceed to Gate B **passive-summary mode**' 'SKILL missing passive-summary branch matrix entry'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$SKILL_MD" '`LOOP_STATUS=emit-plan-failed` — treat as a Step 3 post-apply failure' 'SKILL missing emit-plan-failed branch matrix entry'
contains "$SKILL_MD" 'review-round cap (' 'SKILL missing Step 3 cap breadcrumb prose'
contains "$SKILL_MD" 'skip Gate B, and jump to Step 3b/4/4b with existing artifacts' 'SKILL missing cap short-circuit Gate B bypass'
contains "$SKILL_MD" 'Gate B would otherwise re-surface stale accepted findings from an earlier round' 'SKILL missing stale-finding cap rationale'
contains "$SKILL_MD" 'The Step 3.5 continuation block below is bypassed on this path.' 'SKILL missing explicit Step 3.5 bypass prose'
contains "$SKILL_MD" 'the four primary options are **Approve final design** / **See full plan** / **Discuss further** / **Re-run review panel**' 'SKILL missing Gate C four-option prose'
contains "$SKILL_MD" 'Gate C MUST omit **Re-run review panel** and offer only **Approve final design** / **See full plan** / **Discuss further**' 'SKILL missing Gate C cap-omission prose with See full plan'
contains "$SKILL_MD" 'plan review MUST ALWAYS run the full Step 3 panel' 'SKILL missing full-panel Step 3 contract'

contains "$SKILL_MD" 'sketch_budget=0' 'SKILL must pin SIMPLE sketch_budget=0'
absent "$SKILL_MD" 'review_budget=quick' 'SKILL must not pin v1 review_budget=quick'
absent "$SKILL_MD" 'invoke-plan-validator-if-not-quick.sh' 'SKILL must not reference old validator helper'
absent "$SKILL_MD" 'read-design-review-budget.sh' 'SKILL must not reference old budget reader'
absent "$SKILL_MD" 'NO_SKETCHES_CLASSIFIED_TRIVIAL' 'SKILL must not reference old trivial sentinel'
absent "$SKILL_MD" 'plan-review-quick.md' 'SKILL must not reference deleted quick review reference'
absent "$SKILL_MD" 'design-l3-velocity-notified-2670' 'SKILL must not retain Step 5d velocity comment sentinel'
contains "$SKILL_MD" 'contract drift' 'SKILL missing Step 0b contract-drift abort prose'
contains "$SKILL_MD" 'aborting before silent tier downgrade' 'SKILL missing silent tier downgrade abort pin'
contains "$SKILL_MD" 'bash scripts/test-write-run-params.sh' 'SKILL missing contract-drift repro command'
contains "$SKILL_MD" 'refusing to recreate it with fallback defaults' 'SKILL missing no-fallback run-params warning'
absent "$SKILL_MD" 'run-params write failed; router-flag recovery' 'SKILL must not retain old HARD fallback recovery reason'

contains "$FLAGS_MD" 'Plan-command validator runs unconditionally on both SIMPLE and HARD' 'flags.md missing unconditional validator contract'
contains "$APPROVAL_MD" 'Cap: SIMPLE = 3, HARD = 5' 'approval-gates.md missing tier cap'
contains "$APPROVAL_MD" 'review-round cap (<cap>) reached for <tier>; skipping panel and returning to Gate C.' 'approval-gates.md missing canonical Step 3 cap breadcrumb'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'Gate B passive-summary mode (`LOOP_STATUS=converged|cap-hit`)' 'approval-gates.md missing passive-summary section heading'
# shellcheck disable=SC2016 # Markdown literal contains backticks intentionally.
contains "$APPROVAL_MD" 'Then fire `AskUserQuestion` with exactly two options: **Continue to Step 3.6 and Gate C** (Recommended) / **Switch to discussion mode**.' 'approval-gates.md missing passive-summary Step 3.6 forward link'
contains "$APPROVAL_MD" 'zero-findings short-circuit → Step 3.6 → Step 3b → Step 4 → Step 4b.' 'approval-gates.md missing zero-findings Step 3.6 forward link'
contains "$APPROVAL_MD" 'passive-summary Continue → Step 3.6 → Step 3b → Step 4 → Step 4b' 'approval-gates.md missing passive-summary Gate C Step 3.6 forward link'
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
contains "$DISCUSSION_MD" 'invoke-plan-validator.sh' 'discussion-rounds.md missing renamed validator helper'

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
grep -Fq 'ACTION=EMIT_PLAN' "$SKILL_MD" \
  || fail "(14b1) SKILL.md missing ACTION=EMIT_PLAN emission"
grep -Fq 'ACTION=FINALIZE' "$SKILL_MD" \
  || fail "(14b3) SKILL.md missing ACTION=FINALIZE emission"
grep -Fq 'design-driver.sh' "$SKILL_MD" \
  || fail "(14b4) SKILL.md missing design-driver.sh dispatcher invocation"
grep -Fq 'plan-review-loop.sh' "$SKILL_MD" \
  || fail "(14c0) SKILL.md missing plan-review-loop.sh Step 3 driver invocation"
grep -Fq 'set +e' "$SKILL_MD" \
  || fail "(14c0b) SKILL.md missing set +e guard adjacent to plan-review-loop.sh"
grep -Fq '_plan_review_rc=$?' "$SKILL_MD" \
  || fail "(14c0c) SKILL.md missing _plan_review_rc capture for plan-review-loop.sh"
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

DESIGN_DRIVER_SH="$REPO_ROOT/skills/design/scripts/design-driver.sh"
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
emit_line=$(awk -v s="$step2b_mark" 'NR>s && /ACTION=EMIT_PLAN/ {print NR; exit}' "$SKILL_MD" || true)
val_line=$(awk -v s="$step2b_mark" 'NR>s && /invoke-plan-validator\.sh/ && /plan\.txt/ {print NR; exit}' "$SKILL_MD" || true)
[[ -n "$step2b_mark" && -n "$emit_line" && -n "$val_line" && "$val_line" -gt "$emit_line" ]] \
  || fail "(14b10) VALIDATE_PLAN_COMMANDS must follow EMIT_PLAN in Step 2b block"

AG_MD="$REPO_ROOT/skills/design/references/approval-gates.md"
DR_MD="$REPO_ROOT/skills/design/references/discussion-rounds.md"
[[ -f "$AG_MD" ]] || fail "(14c14a) approval-gates.md missing: $AG_MD"
[[ -f "$DR_MD" ]] || fail "(14c14b) discussion-rounds.md missing: $DR_MD"
grep -Fq 'ACTION=EMIT_PLAN' "$AG_MD" \
  || fail "(14c14c) approval-gates.md missing ACTION=EMIT_PLAN pin"
grep -Fq 'invoke-plan-validator.sh' "$AG_MD" \
  || fail "(14c14d) approval-gates.md missing invoke-plan-validator.sh pin"
emit_before_val_ag=$(awk '/ACTION=EMIT_PLAN/ && !done { e=NR; done=1 } /invoke-plan-validator\.sh/ && !vset { v=NR; vset=1 } END { if (e && v) print (e <= v) ? 1 : 0; else print 0 }' "$AG_MD")
[[ "$emit_before_val_ag" == "1" ]] \
  || fail "(14c14e) approval-gates.md must mention EMIT_PLAN at or before invoke-plan-validator.sh"
grep -Fq 'ACTION=EMIT_PLAN' "$DR_MD" \
  || fail "(14c14f) discussion-rounds.md missing ACTION=EMIT_PLAN pin"
grep -Fq 'invoke-plan-validator.sh' "$DR_MD" \
  || fail "(14c14g) discussion-rounds.md missing invoke-plan-validator.sh pin"
emit_before_val_dr=$(awk '/ACTION=EMIT_PLAN/ && !done { e=NR; done=1 } /invoke-plan-validator\.sh/ && !vset { v=NR; vset=1 } END { if (e && v) print (e <= v) ? 1 : 0; else print 0 }' "$DR_MD")
[[ "$emit_before_val_dr" == "1" ]] \
  || fail "(14c14h) discussion-rounds.md must mention EMIT_PLAN at or before invoke-plan-validator.sh"

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

upsert_line=$(awk -v s="$step5c_line" 'NR>s && /scripts\/upsert-diagrams-comment\.sh/ {print NR; exit}' "$SKILL_MD" || true)
plan_write_line=$(awk -v s="$step5c_line" 'NR>s && /plan-block-write\.sh/ {print NR; exit}' "$SKILL_MD" || true)
publish_line=$(awk -v s="${upsert_line:-0}" 'NR>s && /design-log-publish\.sh/ {print NR; exit}' "$SKILL_MD" || true)
[[ -n "$plan_write_line" && -n "$upsert_line" && -n "$publish_line" && "$plan_write_line" -lt "$upsert_line" && "$upsert_line" -lt "$publish_line" ]] \
  || fail "(15b) Step 5c.5 upsert-diagrams-comment.sh must appear after plan-block-write.sh and before design-log-publish.sh"
step3b_line=$(grep -nF '<!-- step:3b' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
step4_line=$(grep -nF '<!-- step:4 ' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$step3b_line" && -n "$step4_line" ]] || fail "(15b) missing Step 3b or Step 4 marker"
step3b_between=$(sed -n "$((step3b_line + 1)),$((step4_line - 1))p" "$SKILL_MD")
grep -Fq 'architecture-diagram.skipped' <<<"$step3b_between" \
  || fail "(15b) Step 3b must document architecture-diagram.skipped sentinel creation"
step5c_between=$(sed -n "$((step5c_line + 1)),$((step5c_line + 90))p" "$SKILL_MD")
grep -Fq 'architecture-diagram.skipped' <<<"$step5c_between" \
  || fail "(15b) Step 5c.5 must document architecture-diagram.skipped sentinel handling"
grep -Fq -- '--clear-architecture' <<<"$step5c_between" \
  || fail "(15b) Step 5c.5 must invoke --clear-architecture when the skipped sentinel is present"

# Check 17: Step 5b /larch:issue summary-halt guardrails (#2681).
ORCHESTRATOR_NEVER_MD="$REPO_ROOT/skills/shared/orchestrator-never.md"
[[ -f "$ORCHESTRATOR_NEVER_MD" ]] || fail "(17) orchestrator-never.md missing: $ORCHESTRATOR_NEVER_MD"
grep -Fq '5→5a→5b→5c.1→5c.5→5c.7→5c.8→6' "$SKILL_MD" \
  || fail "(17) anti-halt reminder missing intra-Step-5 sub-step enumeration"
grep -Fq "NEVER treat a sub-skill's terminal output as the parent skill's terminal output" "$ORCHESTRATOR_NEVER_MD" \
  || fail "(17) orchestrator-never.md missing sub-skill vs parent-skill terminal-output NEVER literal"
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
emit_line=$(printf '%s\n' "$step2b_block" | grep -nF 'ACTION=EMIT_PLAN' | head -1 | cut -d: -f1 || true)
chk_line=$(printf '%s\n' "$step2b_block" | grep -nF 'skills/design/scripts/check-plan-size.sh' | head -1 | cut -d: -f1 || true)
[[ -n "$emit_line" && -n "$chk_line" ]] || fail "(FINDING_21) could not locate ACTION=EMIT_PLAN / check-plan-size.sh inside Step 2b block"
if ! [[ "$chk_line" -gt "$emit_line" ]]; then
  fail "(FINDING_21) check-plan-size.sh must appear after ACTION=EMIT_PLAN inside Step 2b block"
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
# shellcheck disable=SC2016 # Markdown fence literal in brainstorm.md
grep -Fq '**⚠ Background required — must be paired with breadcrumb-monitor.sh.**' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing background-pair banner in collector fence"
grep -Fq '# Background pair required: see BASH_AUTHORING.md §4' "$BRAINSTORM_MD" \
  || fail "(2754) brainstorm.md missing BASH_AUTHORING §4 in-fence comment"
# shellcheck disable=SC2016 # SKILL.md bash excerpt; quotes are literal
grep -Fq -- '--brainstorm-requested "$brainstorm_requested"' "$SKILL_MD" \
  || fail "(2754) SKILL.md write-run-params invocation missing --brainstorm-requested"
# shellcheck disable=SC2016 # SKILL.md bash excerpt
grep -Fq -- '[[ "$partition_requested" == true || "$brainstorm_requested" == true || "$manual_requested" == true ]]' "$SKILL_MD" \
  || fail "(2754) SKILL.md recovery guard missing partition OR brainstorm OR manual"
# shellcheck disable=SC2016 # jq filter literal
grep -Fq -- '.brainstorm_requested = (.brainstorm_requested == true or $merge_b)' "$SKILL_MD" \
  || fail "(2754) SKILL.md jq merge missing brainstorm_requested arm"
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
# shellcheck disable=SC2016 # Markdown literal contains backticks and "$manual" text intentionally.
grep -Fq 'Parse public flags (`--simple|--hard`, `-p`/`--partition`, `--brainstorm`, `--manual|-m`, `--no-dedup`, `--run-id`)' "$SKILL_MD" \
  || fail "(FINDING_5) SKILL.md Step 0b public-flag parse list missing --manual|-m"
# shellcheck disable=SC2016 # Markdown table cell literal
grep -Fq '| `--manual` / `-m` |' "$SKILL_MD" \
  || fail "(2930) SKILL.md compact flag table missing --manual/-m row"
# shellcheck disable=SC2016 # SKILL.md bash excerpt; quotes are literal
grep -Fq -- '--manual-gate-b "$manual_requested"' "$SKILL_MD" \
  || fail "(2930) SKILL.md write-run-params invocation missing --manual-gate-b"
# shellcheck disable=SC2016 # Markdown literal; backticks are prose, not shell expansion.
grep -Fq 'append `--manual-requested true` only when `manual_requested=true`' "$SKILL_MD" \
  || fail "(FINDING_16) SKILL.md must omit --manual-requested on non-manual runs"
# shellcheck disable=SC2016 # jq filter literal
grep -Fq -- 'manual_gate_b = $merge_m' "$SKILL_MD" \
  || fail "(FINDING_14) SKILL.md jq merge must overwrite manual_gate_b from current argv state"
# shellcheck disable=SC2016 # jq filter literal: $merge_p/$merge_b/$merge_m are jq vars, not shell vars.
grep -Fq -- '.partition_requested = (.partition_requested == true or $merge_p) | .brainstorm_requested = (.brainstorm_requested == true or $merge_b) | .manual_gate_b = $merge_m' "$SKILL_MD" \
  || fail "(#3008) SKILL.md canonical Step 0b jq-merge filter must remain pinned for test-step0b-router-flag-recovery.sh"
# shellcheck disable=SC2016 # SKILL.md bash excerpt; quotes are literal
grep -Fq 'refusing to recreate it with fallback defaults' "$SKILL_MD" \
  || fail "(2930) SKILL.md fallback-missing path must refuse to recreate run-params with defaults"
# shellcheck disable=SC2016 # literal shell snippet anchor in SKILL.md
if grep -Fq -- '--manual-gate-b "${manual_requested:-false}"' "$SKILL_MD"; then
  fail "(2930) SKILL.md must not retain fallback write-run-params --manual-gate-b call"
fi
grep -Fq 'partition, brainstorm, and/or manual requested but jq is unavailable' "$SKILL_MD" \
  || fail "(2930) SKILL.md jq-unavailable warning missing manual"
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
step0b_second_bash=$(awk '
  /^### 0b / { flag=1; next }
  /^### Final summary block$/ && flag { flag=0 }
  flag && /^```bash$/ { c++; next }
  flag && c == 1 && /^```$/ { c=0; next }
  flag && c == 1 { print }
' "$SKILL_MD")
[[ -n "$step0b_second_bash" ]] \
  || fail "(FINDING_13) could not extract Step 0b run-params bash block"
printf '%s\n' "$step0b_second_bash" | grep -Fq 'write-design-current-env.sh' \
  || fail "(FINDING_13) Step 0b run-params bash block must refresh current-design-env before write-run-params"
# shellcheck disable=SC2016 # grep literal contains shell variables and quotes intentionally
printf '%s\n' "$step0b_second_bash" | grep -Fq -- '--issue-number "$ISSUE_NUMBER"' \
  || fail "(FINDING_13) Step 0b current-design-env refresh must pass --issue-number"
# shellcheck disable=SC2016 # grep literal contains shell variables and quotes intentionally
printf '%s\n' "$step0b_second_bash" | grep -Fq -- '--claude-pid "$PPID"' \
  || fail "(FINDING_13) Step 0b current-design-env refresh must pass --claude-pid \"\$PPID\""
printf '%s\n' "$step0b_second_bash" | grep -Fq '_wdce_step0b_args+=(--manual-requested true)' \
  || fail "(FINDING_13) Step 0b current-design-env refresh must add --manual-requested only on manual runs"
step0b_refresh_line=$(printf '%s\n' "$step0b_second_bash" | grep -nF 'write-design-current-env.sh' | head -1 | cut -d: -f1 || true)
step0b_run_params_line=$(printf '%s\n' "$step0b_second_bash" | grep -nF 'write-run-params.sh' | head -1 | cut -d: -f1 || true)
[[ -n "$step0b_refresh_line" && -n "$step0b_run_params_line" ]] \
  || fail "(FINDING_13) could not locate Step 0b refresh and write-run-params lines"
if (( step0b_refresh_line >= step0b_run_params_line )); then
  fail "(FINDING_13) Step 0b must refresh current-design-env before write-run-params"
fi

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
# Check 20 (#2800): Step 0b title-eligibility filter anchors.
grep -Fq '2.5. **Title-eligibility filter**' "$SKILL_MD" \
  || fail "(20) SKILL.md missing Step 0b sub-step 2.5 Title-eligibility filter"
fetch_line=$(grep -n '^2\. \*\*Fetch issue\*\*:' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
filter_line=$(grep -n '^2\.5\. \*\*Title-eligibility filter\*\*' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
clarify_line=$(grep -n '^3\. \*\*Clarify loop\*\*' "$SKILL_MD" | head -1 | cut -d: -f1 || true)
[[ -n "$fetch_line" && -n "$filter_line" && -n "$clarify_line" ]] \
  || fail "(20) Step 0b sub-step 2 / 2.5 / 3 anchors missing"
if (( fetch_line >= filter_line || filter_line >= clarify_line )); then
  fail "(20) Step 0b ordering must be 2 → 2.5 → 3 (lines $fetch_line $filter_line $clarify_line)"
fi
grep -Fq 'title_has_lifecycle_reject_prefix' "$SKILL_MD" \
  || fail "(20) SKILL.md missing title_has_lifecycle_reject_prefix"
grep -Fq "Source \`\${CLAUDE_PLUGIN_ROOT}/scripts/lib-title-eligibility.sh\`." "$SKILL_MD" \
  || fail "(20) SKILL.md missing lib-title-eligibility.sh source line"
grep -Fq 'title_has_archival_report_prefix' "$SKILL_MD" \
  || fail "(20) SKILL.md missing title_has_archival_report_prefix"
grep -Fq 'title_starts_with_brainstorm' "$SKILL_MD" \
  || fail "(20) SKILL.md missing title_starts_with_brainstorm"
grep -Fq 'Mandatory predicate order: (a) lifecycle-reject' "$SKILL_MD" \
  || fail "(20) SKILL.md missing mandatory predicate ordering rule"
grep -Fq 'cancelled-title-filter' "$SKILL_MD" \
  || fail "(20) SKILL.md missing cancelled-title-filter enum"
grep -Fq 'issue title starts with managed lifecycle marker' "$SKILL_MD" \
  || fail "(20) SKILL.md missing lifecycle-reject banner text"
grep -Fq 'issue title matches archival report-prefix' "$SKILL_MD" \
  || fail "(20) SKILL.md missing archival-report-reject banner text"
grep -Fq 'detected Brainstorm title prefix — auto-enabling brainstorm mode' "$SKILL_MD" \
  || fail "(20) SKILL.md missing brainstorm info banner text"
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
grep -Fq '2.5-bis. **Resume detection**' "$SKILL_MD" \
  || fail "(21) SKILL.md missing resume detection sub-step"
grep -Fq 'design-pause-load.sh' "$SKILL_MD" \
  || fail "(21) SKILL.md missing design-pause-load.sh invocation"
grep -Fq '5.5-bis. **Refresh issue-bound env immediately after rename**' "$SKILL_MD" \
  || fail "(21) SKILL.md missing post-rename env refresh"
echo "PASS: (21) /design pause/resume structure anchors OK"

# Checks 24-26 (#2935): /design same-session re-entry guard pins.
step0b_reentry_order=$(awk '
  /^### 0b / { in0b=1; next }
  /^### Final summary block$/ && in0b { in0b=0 }
  in0b && /title_has_lifecycle_reject_prefix/ && !title { title=NR }
  in0b && /design_reentry_marker_hit/ && !guard { guard=NR }
  in0b && /^3\. \*\*Clarify loop\*\*/ && !clarify { clarify=NR }
  END {
    if (!title || !guard || !clarify) exit 2
    if (!(title < guard && guard < clarify)) exit 1
  }
' "$SKILL_MD" || echo "$?")
case "${step0b_reentry_order:-0}" in
  0) ;;
  1|2) fail "(24) SKILL.md missing design_reentry_marker_hit invocation OR sub-step 2.6 placed outside [2.5 .. 3] window" ;;
  *) fail "(24) unexpected Step 0b re-entry guard ordering check exit: ${step0b_reentry_order:-?}" ;;
esac

step5c_reentry_order=$(awk '
  /^### 5c — Write `larch:plan` to GitHub \+ publish$/ { in5c=1; next }
  /^<!-- step:6 / && in5c { in5c=0 }
  in5c && /design_reentry_marker_write/ && !write { write=NR }
  in5c && /tracking-issue-write\.sh" rename --issue "\$ISSUE_NUMBER" --state designed/ && !rename { rename=NR }
  END {
    if (!write || !rename) exit 2
    if (!(write < rename)) exit 1
  }
' "$SKILL_MD" || echo "$?")
case "${step5c_reentry_order:-0}" in
  0) ;;
  1|2) fail "(25) SKILL.md design_reentry_marker_write must precede the [DESIGNED] rename" ;;
  *) fail "(25) unexpected Step 5c re-entry marker ordering check exit: ${step5c_reentry_order:-?}" ;;
esac

grep -Fq '**⚠ /design: refusing spurious re-entry — guard=session-cache' "$SKILL_MD" \
  || fail "(26) SKILL.md missing literal session-cache banner"
grep -Fq 'delete <DESIGN_REENTRY_MARKER_PATH> to override.' "$SKILL_MD" \
  || fail "(26) SKILL.md must document DESIGN_REENTRY_MARKER_PATH in the session-cache banner literal"
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

contains "$SKILL_MD" 'snapshot-plan-round.sh' 'SKILL.md Step 2b missing snapshot-plan-round'
contains "$SKILL_MD" 'write-original --design-tmpdir' 'SKILL.md Step 2b missing write-original invocation'
contains "$SKILL_MD" 'assess-plan-round.sh' 'SKILL.md Step 3.6 missing assess-plan-round.sh'
contains "$SKILL_MD" 'plan-review-round-cursor.txt' 'SKILL.md missing plan-review-round-cursor reference'
contains "$SKILL_MD" 'write-cursor --design-tmpdir' 'SKILL.md missing round-cursor advancement write-cursor'
contains "$SKILL_MD" "--round-num \"\$ROUND_NUM\"" 'SKILL.md missing --round-num ROUND_NUM to plan-review-loop'
contains "$SKILL_MD" 'Step 3.6' 'SKILL.md missing Step 3.6 section'
contains "$SKILL_MD" 'passive-summary Continue, auto-apply, Apply all, or full one-by-one without abort' 'SKILL.md missing passive-summary Step 3.6 settle path'
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
