#!/usr/bin/env bash
# Structural regression test for /implement SKILL.md + larch-log migration.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"
REFS_DIR="$REPO_ROOT/skills/implement/references"
RESTORE_FINALIZE_SH="$REPO_ROOT/scripts/restore-finalize-state.sh"
LIB_FINALIZE_KEYS_SH="$REPO_ROOT/scripts/lib-finalize-state-keys.sh"
SHIP_PR_SH="$REPO_ROOT/scripts/ship-pr.sh"
LINT_FIX_LOOP_SH="$REPO_ROOT/scripts/lint-fix-loop.sh"

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

[[ -f "$SKILL_MD" ]] || fail "skills/implement/SKILL.md missing"
[[ -d "$REFS_DIR" ]] || fail "skills/implement/references missing"

# Issue #2497: /implement docs must not reintroduce removed --auto / --auto-mode flag surfaces.
if grep -Eq '(^|[[:space:]])--auto([^A-Za-z0-9_-]|$)' "$SKILL_MD"; then
  fail "SKILL.md must not document standalone --auto flag token (issue #2497 structural pin)"
fi
grep -Fq -- '--auto-mode' "$SKILL_MD" \
  && fail "SKILL.md must not document --auto-mode flag (issue #2497 structural pin)"

for heading in "## Load-Bearing Invariants" "## NEVER List" "## Rebase Checkpoint Macro"; do
  count="$(grep -c "^$heading$" "$SKILL_MD" || true)"
  [[ "$count" == "1" ]] || fail "expected exactly one $heading heading, found $count"
done

for ref in summary-comment-template.md bump-verification.md codex-manifest-schema.md conflict-resolution.md pr-body-template.md rebase-rebump-subprocedure.md; do
  [[ -f "$REFS_DIR/$ref" ]] || fail "missing reference: $ref"
done

grep -Fq 'scripts/larch-log.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference scripts/larch-log.sh"
grep -Fq 'scripts/tracking-issue-summary.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference scripts/tracking-issue-summary.sh"
grep -Fq 'summary-comment-template.md' "$SKILL_MD" \
  || fail "SKILL.md must reference summary-comment-template.md"

# Pin post-dispatch branch assertion with stable tokens (not "Step 2.2" prose),
# matching `skills/implement/SKILL.md` §2.2 `STATUS=complete` bullet.
# shellcheck disable=SC2016
grep -Fq 'then run **post-dispatch branch assertion** (external-implementer path only): `${CLAUDE_PLUGIN_ROOT}/scripts/git-current-branch.sh` — parse `BRANCH=<name>` into `CURRENT_BRANCH_POST_DISPATCH`' "$SKILL_MD" \
  || fail "SKILL.md must retain post-dispatch branch assertion contract (git-current-branch.sh + CURRENT_BRANCH_POST_DISPATCH)"
grep -Fq 'FINAL_BAIL_REASON=main-branch-post-dispatch' "$SKILL_MD" \
  || fail "SKILL.md must document FINAL_BAIL_REASON=main-branch-post-dispatch (post-dispatch mismatch bail)"

if grep -Eiq '(^|[^[:alpha:]])user has( made| fixed)?([^[:alpha:]]|$)' \
    "$SKILL_MD" \
    "$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.md" \
    "$REPO_ROOT/skills/review-and-fix/scripts/review-and-fix.sh"; then
  fail "orchestrator/review-fix docs must not attribute coder work as 'user has...'"
fi

old_surfaces=(anchor-section-markers.sh assemble-anchor.sh hydrate-anchor.sh refresh-anchor.sh upsert-anchor find-anchor ANCHOR_COMMENT_ID "\$IMPLEMENT_TMPDIR/anchor-sections")
for old in "${old_surfaces[@]}"; do
  if grep -Fq "$old" "$SKILL_MD"; then
    fail "SKILL.md still references removed anchor surface: $old"
  fi
done

grep -Fq 'code-quality / risk-integration / correctness / architecture' "$SKILL_MD" \
  || fail "focus-area enum missing"
grep 'code-quality / risk-integration / correctness / architecture' "$SKILL_MD" | grep -q 'security' \
  || fail "focus-area enum line must include security"

grep -Fq '### Larch-log batches' "$SKILL_MD" \
  || fail "SKILL.md must contain the Larch-log batches section heading"
# shellcheck disable=SC2016
grep -qE 'NEVER write, recreate, or modify .\$IMPLEMENT_TMPDIR/finalize-state\.sh' "$SKILL_MD" \
  || fail "SKILL.md must contain NEVER bullet for finalize-state.sh write prohibition"

step18_order_status=0
awk '
  /<!-- step:18/ {
    in_step = 1
    next
  }
  in_step && /<!-- step:/ {
    in_step = 0
    in_bash = 0
  }
  in_step && /^```(bash|sh|shell)[[:space:]]*$/ {
    in_bash = 1
    next
  }
  in_step && in_bash && /^```[[:space:]]*$/ {
    in_bash = 0
    next
  }
  in_step && in_bash && restore_line == 0 && /\/scripts\/restore-finalize-state\.sh/ {
    restore_line = NR
  }
  in_step && in_bash && teardown_line == 0 && /\/scripts\/implement-finalize\.sh.*teardown/ {
    teardown_line = NR
  }
  END {
    if (restore_line == 0) exit 10
    if (teardown_line == 0) exit 11
    if (restore_line >= teardown_line) exit 12
  }
' "$SKILL_MD" || step18_order_status=$?
case "$step18_order_status" in
  0) ;;
  10) fail "restore-finalize-state.sh not found in Step 18 region" ;;
  11) fail "implement-finalize.sh teardown not found in Step 18 region" ;;
  12) fail "restore-finalize-state.sh must appear before implement-finalize.sh teardown in Step 18" ;;
  *) fail "unexpected Step 18 finalize-state order check failure: $step18_order_status" ;;
esac

[[ -f "$RESTORE_FINALIZE_SH" ]] || fail "scripts/restore-finalize-state.sh missing"
[[ -x "$RESTORE_FINALIZE_SH" ]] || fail "scripts/restore-finalize-state.sh must be executable"
[[ -f "$REPO_ROOT/scripts/restore-finalize-state.md" ]] || fail "scripts/restore-finalize-state.sh must have sibling restore-finalize-state.md"

[[ -f "$LINT_FIX_LOOP_SH" ]] || fail "scripts/lint-fix-loop.sh missing"
[[ -x "$LINT_FIX_LOOP_SH" ]] || fail "scripts/lint-fix-loop.sh must be executable"
[[ -f "$REPO_ROOT/scripts/lint-fix-loop.md" ]] || fail "scripts/lint-fix-loop.sh must have sibling lint-fix-loop.md"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-quiet\.sh' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must source lib-quiet.sh"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-cursor-launcher-common\.sh' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must source lib-cursor-launcher-common.sh"
grep -Fq 'run-external-agent.sh' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must dispatch through run-external-agent.sh"

step3_lint_status=0
awk '
  /<!-- step:3/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /lint-fix-loop\.sh/ { found = 1 }
  END { if (!found) exit 1 }
' "$SKILL_MD" || step3_lint_status=$?
[[ "$step3_lint_status" == "0" ]] || fail "Step 3 region must reference lint-fix-loop.sh"

step6_lint_status=0
awk '
  /<!-- step:6/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /lint-fix-loop\.sh/ { found = 1 }
  END { if (!found) exit 1 }
' "$SKILL_MD" || step6_lint_status=$?
[[ "$step6_lint_status" == "0" ]] || fail "Step 6 region must reference lint-fix-loop.sh"

step5_lint_status=0
awk '
  /<!-- step:5/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /lint-fix-loop\.sh/ { found = 1 }
  END { if (!found) exit 1 }
' "$SKILL_MD" || step5_lint_status=$?
[[ "$step5_lint_status" == "0" ]] || fail "Step 5 region must reference lint-fix-loop.sh"

if grep -Eiq 'diagnose([[:space:]]*,[[:space:]]*|[[:space:]]*\+[[:space:]]*)fix' "$SKILL_MD"; then
  fail "SKILL.md must not contain bare diagnose/fix relevant-checks loops without lint-fix-loop.sh routing"
fi

# Pin that ship-pr.sh run_checks_phase calls lint-fix-loop.sh internally, so the
# orchestrator never needs to fix PHASE=checks failures via main-agent Edit/Write.
grep -q 'lint-fix-loop\.sh' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must reference lint-fix-loop.sh (run_checks_phase call site)"
grep -q 'ship-pr-ci-initial' "$SHIP_PR_SH" \
  || fail "ship-pr.sh run_checks_phase must pass --site ship-pr-ci-initial to lint-fix-loop.sh"
grep -q 'ship-pr-ci-initial' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must accept --site ship-pr-ci-initial"
grep -q 'ship-pr-ci-merge' "$SHIP_PR_SH" \
  || fail "ship-pr.sh CI failure recovery must pass --site ship-pr-ci-merge to lint-fix-loop.sh"
grep -q 'ship-pr-ci-merge' "$LINT_FIX_LOOP_SH" \
  || fail "lint-fix-loop.sh must accept --site ship-pr-ci-merge"

# Step 8+ Exit 3: first-fixer-non-health autonomous sub-procedure (ordered 1–12) must be documented.
step8_exit3_status=0
awk '
  /## Step 8\+/ { in8 = 1; next }
  in8 && /^## / { in8 = 0 }
  in8 && /\*\*Exit 3\*\*/ { in_exit3 = 1 }
  in_exit3 && /^- \*\*Exit [0-9]/ && !/\*\*Exit 3\*\*/ { in_exit3 = 0 }
  in_exit3 {
    if ($0 ~ /first-fixer-non-health/) f = 1
    if ($0 ~ /^  1\./) s1 = 1
    if ($0 ~ /^  12\./) s12 = 1
  }
  END { if (!(f && s1 && s12)) exit 1 }
' "$SKILL_MD" || step8_exit3_status=$?
[[ "$step8_exit3_status" == "0" ]] || fail "SKILL.md Step 8+ Exit 3 must document first-fixer-non-health and autonomous sub-steps 1 through 12"

# Pin LAUNCHER_FAILURE_* canonical tokens across classifier, launchers, and ship-pr guard.
for _pin in none health other auth binary-missing health-probe timeout parse refusal unknown; do
  grep -Fq "$_pin" "$REPO_ROOT/scripts/lib-external-launcher-common.sh" \
    || fail "lib-external-launcher-common.sh must contain canonical token: $_pin"
done
for _pin in none health other auth binary-missing health-probe timeout parse refusal unknown; do
  grep -Fq "$_pin" "$REPO_ROOT/scripts/launch-cursor-ci.sh" \
    || fail "launch-cursor-ci.sh must contain canonical token: $_pin"
  grep -Fq "$_pin" "$REPO_ROOT/scripts/launch-codex-ci.sh" \
    || fail "launch-codex-ci.sh must contain canonical token: $_pin"
  grep -Fq "$_pin" "$REPO_ROOT/scripts/launch-claude-ci.sh" \
    || fail "launch-claude-ci.sh must contain canonical token: $_pin"
done
grep -Fq 'first-fixer-non-health' "$REPO_ROOT/scripts/ship-pr.sh" \
  || fail "ship-pr.sh must reference first-fixer-non-health"
grep -Fq 'LAUNCHER_FAILURE_CLASS' "$REPO_ROOT/scripts/ship-pr.sh" \
  || fail "ship-pr.sh must reference LAUNCHER_FAILURE_CLASS"

[[ -f "$LIB_FINALIZE_KEYS_SH" ]] || fail "scripts/lib-finalize-state-keys.sh missing"
[[ -f "$REPO_ROOT/scripts/lib-finalize-state-keys.md" ]] || fail "scripts/lib-finalize-state-keys.sh must have sibling lib-finalize-state-keys.md"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-finalize-state-keys\.sh' "$RESTORE_FINALIZE_SH" \
  || fail "restore-finalize-state.sh must source lib-finalize-state-keys.sh"
grep -qE '^[[:space:]]*(source|\.)[[:space:]].*lib-finalize-state-keys\.sh' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must source lib-finalize-state-keys.sh"

# shellcheck disable=SC2016
grep -Fq 'POST_PLAN_WORKFLOW_PATH=HARD' "$SKILL_MD" \
  || fail "Post-plan router must default POST_PLAN_WORKFLOW_PATH=HARD (cutover removed --hard flag)"
# Post-cutover: /implement no longer accepts --hard, so hard_mode references must be gone.
! grep -Fq 'hard_mode' "$SKILL_MD" \
  || fail "Post-plan router must not reference hard_mode (--hard flag removed in cutover)"
# Post-cutover: plan materialization uses conventional $IMPLEMENT_TMPDIR/plan.txt; do not resurrect persist-post-plan-keys.
! grep -Fq 'persist-post-plan-keys' "$SKILL_MD" \
  || fail "skills/implement/SKILL.md must not reference persist-post-plan-keys (retired #2487)"
! grep -Fq 'post-design-boundary.sh' "$SKILL_MD" \
  || fail "skills/implement/SKILL.md must not reference post-design-boundary.sh (retired #2487)"
grep -Fq 'scripts/persist-implement-run-flags.sh' "$SKILL_MD" \
  || fail "Post-plan router must invoke scripts/persist-implement-run-flags.sh"

step17_status=0
awk '
  /<!-- step:17/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /Fork CI Dry-Run Complete/ { bad = 1 }
  in_step && /--draft was set/ { bad = 1 }
  in_step && /--merge was not set/ { bad = 1 }
  in_step && /--design-only was set/ { bad = 1 }
  in_step && /write-final-report\.sh.*--print-stdout/ { good = 1 }
  END { if (bad) exit 2; if (!good) exit 1 }
' "$SKILL_MD" || step17_status=$?
[[ "$step17_status" == "0" ]] || fail "SKILL.md Step 17 must drop branched prose and use write-final-report.sh --print-stdout"

step18_status=0
awk '
  /<!-- step:18/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0 }
  in_step && /write-final-report\.sh".*--print-stdout/ { bad = 1 }
  END { if (bad) exit 2; exit 0 }
' "$SKILL_MD" || step18_status=$?
[[ "$step18_status" == "0" ]] || fail "SKILL.md Step 18 write-final-report.sh must NOT use --print-stdout (silent refresh only; FINDING_1)"

COMMIT_IMPL_SH="$REPO_ROOT/skills/implement/scripts/commit-implementation.sh"
COMMIT_REVIEW_SH="$REPO_ROOT/skills/implement/scripts/commit-review-fixes.sh"
STEP_7A_SH="$REPO_ROOT/skills/implement/scripts/step-7a.sh"
GEN_DIAGRAM_SH="$REPO_ROOT/skills/implement/scripts/generate-code-flow-diagram.sh"

[[ -f "$COMMIT_IMPL_SH" ]] || fail "skills/implement/scripts/commit-implementation.sh missing"
grep -qF 'timing-ledger.sh" mark "Step 4 — commit implementation"' "$COMMIT_IMPL_SH" \
  || fail "commit-implementation.sh must contain Step 4 timing-ledger mark"

[[ -f "$COMMIT_REVIEW_SH" ]] || fail "skills/implement/scripts/commit-review-fixes.sh missing"
grep -qF 'timing-ledger.sh" mark "Step 7 — commit review fixes"' "$COMMIT_REVIEW_SH" \
  || fail "commit-review-fixes.sh must contain Step 7 timing-ledger mark"

[[ -f "$STEP_7A_SH" ]] || fail "skills/implement/scripts/step-7a.sh missing"
grep -qF 'timing-ledger.sh" mark "Step 7a — code flow diagram"' "$STEP_7A_SH" \
  || fail "step-7a.sh must contain Step 7a timing-ledger mark"
[[ -f "$GEN_DIAGRAM_SH" ]] || fail "skills/implement/scripts/generate-code-flow-diagram.sh missing"
grep -qF 'timing-ledger.sh" mark "Step 7a — code flow diagram"' "$GEN_DIAGRAM_SH" \
  && fail "generate-code-flow-diagram.sh must not contain Step 7a timing-ledger mark (consolidated into step-7a.sh)"

# Pin Exit 4 handling in SKILL.md: must direct orchestrator to "Continue to Step 16"
exit4_step16_status=0
awk '
  /\*\*Exit 4\*\*/ { window = 15 }
  window > 0 && /Continue to Step 16/ { found = 1 }
  window > 0 { window-- }
  END { if (!found) exit 1 }
' "$SKILL_MD" || exit4_step16_status=$?
[[ "$exit4_step16_status" == "0" ]] || fail "SKILL.md Exit 4 prose must direct orchestrator to 'Continue to Step 16'"

# Pin that ship-pr.sh STALL_STEP=12d branch emits the branch-local diagnostic.
stall12d_directive_status=0
awk '
  /policy_denied\|admin_failed\|error\)/ { in_branch = 1 }
  in_branch && /ORCHESTRATOR DIRECTIVE \(STALL_STEP=12d\)/ { found_banner = 1 }
  in_branch && /DO NOT improvise recovery\./ { found_directive = 1 }
  in_branch && /exit 4/ {
    if (found_banner && found_directive) {
      success = 1
      exit 0
    }
    exit 1
  }
  END { if (!success) exit 1 }
' "$SHIP_PR_SH" || stall12d_directive_status=$?
[[ "$stall12d_directive_status" == "0" ]] \
  || fail "ship-pr.sh must emit the ORCHESTRATOR DIRECTIVE (STALL_STEP=12d) DO NOT improvise diagnostic on the STALL_STEP=12d exit 4 path"

# shellcheck disable=SC2016
grep -Fq 'if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then main' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must gate main behind BASH_SOURCE vs argv0 (source-safe entry)"
grep -Fq 'recovery_waterfall_paths_delta_revert' "$SHIP_PR_SH" \
  || fail "ship-pr.sh must define recovery_waterfall_paths_delta_revert (rollback helper)"
# shellcheck disable=SC2016
grep -Fq 'git restore --staged -- "$path"' "$SHIP_PR_SH" \
  || fail "ship-pr recovery rollback must use git restore --staged with a quoted path operand (FINDING_14/F23)"
grep -Fq 'while IFS= read -r path' "$SHIP_PR_SH" \
  || fail "ship-pr recovery rollback must iterate paths with IFS= read -r (safe for spaces/globs)"

grep -Fq '**Terminal disposition invariant:**' "$SKILL_MD" \
  || fail "SKILL.md must retain OOS Terminal disposition invariant paragraph"

grep -Fq 'NEVER silently drop a voted-in OOS finding' "$SKILL_MD" \
  || fail "SKILL.md must retain NEVER rule prohibiting silent OOS drops"

# shellcheck disable=SC2016
grep -Fq 'NEVER set `OOS_PENDING=false` without a passing `oos-disposition-gate.sh` invocation' "$SKILL_MD" \
  || fail "SKILL.md must retain NEVER #18 gate-before-clear pin (OOS_PENDING vs oos-disposition-gate.sh)"

# Folded Step 0 / admission structural pins (fix-issue removal; Step 0 + Preflight admission)
grep -Fq 'scripts/implement-admission.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference scripts/implement-admission.sh"
grep -Fq '1. **Admission gate**' "$SKILL_MD" \
  || fail "SKILL.md Preflight must contain numbered Admission gate step"
grep -Fq '**Preflight — admission gate known limitation (D3)**' "$SKILL_MD" \
  || fail "SKILL.md must document admission gate fail-open limitation (D3)"
# shellcheck disable=SC2016
grep -Fq '6. **On `AUDIT=pass` — semantic materiality (comment-only)**' "$SKILL_MD" \
  || fail "SKILL.md Preflight must retain semantic materiality step (item 6)"
grep -Fq 'semantic stale notice posted at Preflight item 6' "$SKILL_MD" \
  || fail "SKILL.md exit table must pin Preflight item 6 semantic stale path"
grep -Fq '### Step 0 — tracking issue adoption' "$SKILL_MD" \
  || fail "SKILL.md must contain Step 0 tracking issue adoption heading"
grep -Fq '### Plan materialization from issue body' "$SKILL_MD" \
  || fail "SKILL.md must contain plan materialization heading"
read -r tok0_track <<'EOF'
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 0 — tracking issue"
EOF
read -r time0_track <<'EOF'
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 0 — tracking issue"
EOF
read -r tok0_plan <<'EOF'
"${CLAUDE_PLUGIN_ROOT}/scripts/token-ledger.sh" mark "Step 0 — plan materialization"
EOF
read -r time0_plan <<'EOF'
"${CLAUDE_PLUGIN_ROOT}/scripts/timing-ledger.sh" mark "Step 0 — plan materialization"
EOF
grep -Fq "$tok0_track" "$SKILL_MD" \
  || fail "SKILL.md must retain token-ledger Step 0 — tracking issue mark"
grep -Fq "$time0_track" "$SKILL_MD" \
  || fail "SKILL.md must retain timing-ledger Step 0 — tracking issue mark"
grep -Fq '# token-mark Step 0 — tracking issue' "$SKILL_MD" \
  || fail "SKILL.md must retain token-mark Step 0 — tracking issue comment pair"
grep -Fq '# timing-mark Step 0 — tracking issue' "$SKILL_MD" \
  || fail "SKILL.md must retain timing-mark Step 0 — tracking issue comment pair"
grep -Fq "$tok0_plan" "$SKILL_MD" \
  || fail "SKILL.md must retain token-ledger Step 0 — plan materialization mark"
grep -Fq "$time0_plan" "$SKILL_MD" \
  || fail "SKILL.md must retain timing-ledger Step 0 — plan materialization mark"
grep -Fq '# token-mark Step 0 — plan materialization' "$SKILL_MD" \
  || fail "SKILL.md must retain token-mark Step 0 — plan materialization comment pair"
grep -Fq '# timing-mark Step 0 — plan materialization' "$SKILL_MD" \
  || fail "SKILL.md must retain timing-mark Step 0 — plan materialization comment pair"
if grep -Fq '<!-- step:0.5' "$SKILL_MD"; then
  fail "SKILL.md must not reintroduce <!-- step:0.5 session anchor"
fi
if grep -Fq '<!-- step:1 —' "$SKILL_MD"; then
  fail "SKILL.md must not reintroduce retired <!-- step:1 — session anchor"
fi
if grep -Fq '### /fix-issue coordination' "$SKILL_MD"; then
  fail "SKILL.md must not contain /fix-issue coordination subsection"
fi

# Drift guard: ship-pr write_initial_state printf keys vs SKILL.md Required keys bullets
# (pinned region between <!-- write-initial-state-keys:begin/end --> markers).
if ! grep -Fq '<!-- write-initial-state-keys:begin -->' "$SKILL_MD"; then
  fail "skills/implement/SKILL.md missing <!-- write-initial-state-keys:begin --> marker (ship-pr state-key drift guard)"
fi
if ! grep -Fq '<!-- write-initial-state-keys:end -->' "$SKILL_MD"; then
  fail "skills/implement/SKILL.md missing <!-- write-initial-state-keys:end --> marker (ship-pr state-key drift guard)"
fi

skill_keys=$(
  awk '/<!-- write-initial-state-keys:begin -->/{flag=1; next} /<!-- write-initial-state-keys:end -->/{flag=0} flag' "$SKILL_MD" \
    | sed 's/^- //' \
    | grep -oE '`[A-Z_][A-Z0-9_]*' | tr -d '`' | sort -u
)

ship_keys=$(
  awk '/^write_initial_state\(\) \{/,/\} > "\$tmp" && mv/' "$SHIP_PR_SH" \
    | grep -E "^[[:space:]]*printf '[A-Z_][A-Z0-9_]*=" \
    | sed -E "s/^[[:space:]]*printf '//; s/=.*//" | sort -u
)

skill_n=$(printf '%s\n' "$skill_keys" | grep -c . || true)
ship_n=$(printf '%s\n' "$ship_keys" | grep -c . || true)
[[ "$skill_n" -ge 20 ]] \
  || fail "write-initial-state drift guard: extracted only ${skill_n} SKILL.md keys (<20) — parser regression or empty marker region"
[[ "$ship_n" -ge 20 ]] \
  || fail "write-initial-state drift guard: extracted only ${ship_n} ship-pr.sh keys (<20) — write_initial_state() structure may have changed"

diff_ship_not_skill=$(comm -23 <(printf '%s\n' "$ship_keys") <(printf '%s\n' "$skill_keys") || true)
diff_skill_not_ship=$(comm -13 <(printf '%s\n' "$ship_keys") <(printf '%s\n' "$skill_keys") || true)
if [[ -n "$diff_ship_not_skill" ]]; then
  echo "Keys in ship-pr.sh missing from SKILL.md:" >&2
  printf '%s\n' "$diff_ship_not_skill" >&2
fi
if [[ -n "$diff_skill_not_ship" ]]; then
  echo "Keys in SKILL.md missing from ship-pr.sh:" >&2
  printf '%s\n' "$diff_skill_not_ship" >&2
fi
if [[ -n "$diff_ship_not_skill" || -n "$diff_skill_not_ship" ]]; then
  fail "write_initial_state key set drift between skills/implement/SKILL.md (write-initial-state-keys region) and scripts/ship-pr.sh write_initial_state()"
fi

grep -Fq "seed \`\$IMPLEMENT_TMPDIR/ship-pr-state.sh\` from the canonical Step 8 \`<!-- write-initial-state-keys:begin/end -->\` required-key block" "$SKILL_MD" \
  || fail "SKILL.md Step 5 stall path must pin the canonical write-initial-state-keys block as the ship-pr-state seed source"
grep -Fq 'copy the full canonical key set' "$SKILL_MD" \
  || fail "SKILL.md Step 5 stall path must require copying the full canonical ship-pr-state key set"

echo "All assertions passed."
