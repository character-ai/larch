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
grep -Fq 'tracking-issue-summary.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference tracking-issue-summary.sh"
grep -Fq 'summary-comment-template.md' "$SKILL_MD" \
  || fail "SKILL.md must reference summary-comment-template.md"

# Pin post-dispatch branch assertion with stable tokens (not "Step 2.2" prose),
# matching `skills/implement/SKILL.md` §2.2 `STATUS=complete` bullet.
# shellcheck disable=SC2016
grep -Fq 'then run **post-dispatch branch assertion** (external-implementer path only): `${CLAUDE_PLUGIN_ROOT}/scripts/git-current-branch.sh` — parse `BRANCH=<name>` into `CURRENT_BRANCH_POST_DISPATCH`' "$SKILL_MD" \
  || fail "SKILL.md must retain post-dispatch branch assertion contract (git-current-branch.sh + CURRENT_BRANCH_POST_DISPATCH)"
grep -Fq 'FINAL_BAIL_REASON=main-branch-post-dispatch' "$SKILL_MD" \
  || fail "SKILL.md must document FINAL_BAIL_REASON=main-branch-post-dispatch (post-dispatch mismatch bail)"
grep -Fq '### Step 18a — Stall recovery gate' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 18a stall recovery heading"
grep -Fq '### Step 18b — Teardown' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 18b teardown heading"
grep -Fq '⏩ 18a: stall recovery — no stall detected' "$SKILL_MD" \
  || fail "SKILL.md must retain the Step 18a no-stall fast-path line"
STALL_RECOVERY_MD="$REPO_ROOT/skills/implement/references/stall-recovery.md"
STALL_RECOVERY_HELPER_SH="$REPO_ROOT/skills/implement/scripts/stall-recovery-report.sh"
grep -Fq 'BAIL_FAILURE_DETAIL_LOG' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must route BAIL_FAILURE_DETAIL_LOG into Step 18a classification"
# shellcheck disable=SC2016
grep -Fq '[--failure-detail-log "$VALIDATED_BAIL_FAILURE_DETAIL_LOG"]' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must document validated --failure-detail-log handoff for classify"
# shellcheck disable=SC2016
grep -Fq 'retry-policy --class "$FAILURE_CLASS"' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must mechanically gate dispatch with retry-policy"
# shellcheck disable=SC2016
grep -Fq 'If `attempt_count >= MAX_ATTEMPTS`, do not dispatch; continue directly to terminal-failure handling.' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must fail closed when retry caps are exhausted before dispatch"
grep -Fq 'PHASE=ci-initial' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md terminal-failure path must seed canonical Step-8-shaped state"
grep -Fq 'BAIL_FAILURE_DETAIL_LOG=' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md terminal-failure path must preserve or seed BAIL_FAILURE_DETAIL_LOG"
grep -Fq '### Step 18a — Stall recovery gate' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 18a heading"
grep -Fq '### Step 18b — Teardown' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 18b heading"
# shellcheck disable=SC2016
grep -Fq 'If in-memory `STALL_TRACKING=false`, `STALL_TRACKING_DISK` is false or empty, and `STALL_TRACKING_SESSION` is false or empty, print `⏩ 18a: stall recovery — no stall detected` and continue to Step 18b.' "$SKILL_MD" \
  || fail "SKILL.md must require all three stall-tracking layers false before the Step 18a no-stall fast path"

stall_step18a_tmp=$(mktemp -d "${TMPDIR:-/tmp}/larch-step18a-structure.XXXXXX")
cat >"$stall_step18a_tmp/ship-pr-state.sh" <<'EOF'
PHASE=ci-initial
STALL_TRACKING=true
STALL_STEP=8
BAIL_REASON=
EXIT_CODE=4
NOTE=network timeout
EOF
mkdir -p "$stall_step18a_tmp/bin"
printf '#!/usr/bin/env bash\necho "$@" >>"%s/gh.calls"\n' "$stall_step18a_tmp" >"$stall_step18a_tmp/bin/gh"
chmod +x "$stall_step18a_tmp/bin/gh"
LARCH_QUIET_DISABLE=1 "$STALL_RECOVERY_HELPER_SH" init-attempts --implement-tmpdir "$stall_step18a_tmp" --attempts-file "$stall_step18a_tmp/attempts.env" >/dev/null
LARCH_QUIET_DISABLE=1 "$STALL_RECOVERY_HELPER_SH" classify --implement-tmpdir "$stall_step18a_tmp" --attempts-file "$stall_step18a_tmp/attempts.env" >"$stall_step18a_tmp/class.env"
PATH="$stall_step18a_tmp/bin:$PATH" LARCH_QUIET_DISABLE=1 LARCH_STALL_RECOVERY_DRY_RUN=1 "$STALL_RECOVERY_HELPER_SH" bug-body --implement-tmpdir "$stall_step18a_tmp" --classification-file "$stall_step18a_tmp/class.env" >"$stall_step18a_tmp/body.out"
PATH="$stall_step18a_tmp/bin:$PATH" LARCH_QUIET_DISABLE=1 LARCH_STALL_RECOVERY_DRY_RUN=1 "$STALL_RECOVERY_HELPER_SH" issue-input-file --implement-tmpdir "$stall_step18a_tmp" --classification-file "$stall_step18a_tmp/class.env" --body-file "$stall_step18a_tmp/stall-recovery-bug-body.md" >"$stall_step18a_tmp/input.out"
grep -Fq '## Action required — file larch bug' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must retain the consumer Action-required print path"
grep -Fq '### [Bug] /implement stall: transient-infra at 8' "$stall_step18a_tmp/stall-recovery-issue-input.md" \
  || fail "Step 18a dry-run integration must generate the expected /larch:issue title"
grep -Fq '## Sanitized stall report' "$stall_step18a_tmp/stall-recovery-bug-body.md" \
  || fail "Step 18a dry-run integration must generate the consumer chat body"
if [ -f "$stall_step18a_tmp/gh.calls" ]; then
  fail "Step 18a dry-run integration must not invoke gh"
fi
rm -rf "$stall_step18a_tmp"

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

grep -Fq 'scripts/larch-log-batches.md' "$REPO_ROOT/docs/run-logs.md" "$REPO_ROOT/scripts/implement-bootstrap.md" \
  || fail "run-log docs must retain larch-log batch table pointer"
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
grep -Fq -- '--workflow-path HARD' "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must persist HARD workflow path"
# Post-cutover: /implement no longer accepts --hard, so hard_mode references must be gone.
! grep -Fq 'hard_mode' "$SKILL_MD" \
  || fail "Post-plan router must not reference hard_mode (--hard flag removed in cutover)"
# Post-cutover: plan materialization uses conventional $IMPLEMENT_TMPDIR/plan.txt; do not resurrect persist-post-plan-keys.
! grep -Fq 'persist-post-plan-keys' "$SKILL_MD" \
  || fail "skills/implement/SKILL.md must not reference persist-post-plan-keys (retired #2487)"
! grep -Fq 'post-design-boundary.sh' "$SKILL_MD" \
  || fail "skills/implement/SKILL.md must not reference post-design-boundary.sh (retired #2487)"
grep -Fq 'persist-implement-run-flags.sh' "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must invoke persist-implement-run-flags.sh"

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
  in_step && /_wfr_args\+=\(--print-stdout\)/ { print_guard = 1 }
  in_step && /cmp -s "\$IMPLEMENT_TMPDIR\/\.step18-prebody" "\$IMPLEMENT_TMPDIR\/summary-final\.md"/ { cmp_guard = 1 }
  END { if (!print_guard || !cmp_guard) exit 1; exit 0 }
' "$SKILL_MD" || step18_status=$?
[[ "$step18_status" == "0" ]] || fail "SKILL.md Step 18 write-final-report.sh must request --print-stdout only through the guarded body-diff path"

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
! grep -Fq '### Step 0 — tracking issue adoption' "$SKILL_MD" \
  || fail "SKILL.md must not reintroduce prompt-side Step 0 tracking issue adoption heading"
! grep -Fq '### Plan materialization from issue body' "$SKILL_MD" \
  || fail "SKILL.md must not reintroduce prompt-side plan materialization heading"
! grep -Fq '### Implementer waterfall' "$SKILL_MD" \
  || fail "SKILL.md must not reintroduce prompt-side implementer waterfall heading"
read -r tok0_plan_bootstrap <<'EOF'
"$SCRIPT_DIR/token-ledger.sh" mark "implement Step 0 — plan materialization"
EOF
read -r time0_plan_bootstrap <<'EOF'
"$SCRIPT_DIR/timing-ledger.sh" mark "implement Step 0 — plan materialization"
EOF
grep -Fq "$tok0_plan_bootstrap" "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must retain token-ledger implement Step 0 — plan materialization mark"
grep -Fq "$time0_plan_bootstrap" "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must retain timing-ledger implement Step 0 — plan materialization mark"
grep -Fq 'phase_coder_select' "$SKILL_MD" \
  || fail "SKILL.md must pin coder selection ownership to implement-bootstrap.sh"
grep -Fq 'mark "implement Step 0 — coder select"' "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must contain coder-select token/timing mark"
grep -Fq '_ib_preflight=()' "$SKILL_MD" \
  || fail "SKILL.md must retain the _ib_preflight argv array"
read -r preflight_wire_line <<'EOF'
[ -n "${PREFLIGHT_TMPDIR:-}" ] && _ib_preflight+=(--preflight-tmpdir "$PREFLIGHT_TMPDIR")
EOF
grep -Fq "$preflight_wire_line" "$SKILL_MD" \
  || fail "SKILL.md must wire PREFLIGHT_TMPDIR through _ib_preflight"
read -r preflight_expand_line <<'EOF'
"${_ib_preflight[@]+"${_ib_preflight[@]}"}"
EOF
if [ "$(grep -cF "$preflight_expand_line" "$SKILL_MD" || true)" -lt 1 ]; then
  fail "SKILL.md must expand _ib_preflight in the bootstrap invocation"
fi
grep -Fq -- '--resume-plan-tail' "$REPO_ROOT/scripts/implement-bootstrap.md" \
  || fail "implement-bootstrap.md must document --resume-plan-tail"
grep -Fq -- '--resume-plan-tail' "$SKILL_MD" \
  || fail "SKILL.md must retain dirty-tree resume-tail routing"
read -r target_issue_line <<'EOF'
_ib_target_issue="${TARGET_ISSUE_NUMBER:-${ISSUE_NUMBER:-}}"
EOF
grep -Fq "$target_issue_line" "$SKILL_MD" \
  || fail "SKILL.md must reuse TARGET_ISSUE_NUMBER fallback"
read -r bootstrap_rc_guard_line <<'EOF'
if [ "$_ib_rc" -eq 2 ]; then
EOF
if [ "$(grep -cF "$bootstrap_rc_guard_line" "$SKILL_MD" || true)" -lt 1 ]; then
  fail "SKILL.md must keep bootstrap exit-2 wrapper"
fi
grep -Fq "while IFS= read -r _ib_line || [ -n \"\$_ib_line\" ]; do" "$SKILL_MD" \
  || fail "SKILL.md must parse bootstrap stdout"
grep -Fq "BRANCH_NAME=*) BRANCH_NAME=\${_ib_tok#BRANCH_NAME=} ;;" "$SKILL_MD" \
  || fail "SKILL.md must retain BRANCH_NAME _ib_kv_scan case arm"
grep -Fq "BRANCH_ACTION=*) BRANCH_ACTION=\${_ib_tok#BRANCH_ACTION=} ;;" "$SKILL_MD" \
  || fail "SKILL.md must retain BRANCH_ACTION _ib_kv_scan case arm"
grep -Fq "PLAN_FILE=*) PLAN_FILE=\${_ib_tok#PLAN_FILE=} ;;" "$SKILL_MD" \
  || fail "SKILL.md must retain PLAN_FILE _ib_kv_scan case arm"
grep -Fq "coder=*) coder=\${_ib_tok#coder=} ;;" "$SKILL_MD" \
  || fail "SKILL.md must retain coder _ib_kv_scan case arm"

step0_plan_structure_status=0
awk '
  /<!-- step:0/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0; in_bash = 0 }
  in_step && /^```(bash|sh|shell)[[:space:]]*$/ { in_bash = 1; next }
  in_step && in_bash && /^```[[:space:]]*$/ { in_bash = 0; next }
  in_step && in_bash {
    if ($0 ~ /_ib_out=\$\("\$\{CLAUDE_PLUGIN_ROOT\}\/scripts\/implement-bootstrap\.sh" --up-to-phase coder/) bootstrap_calls++
    if ($0 ~ /--up-to-phase coder/) coder_literal++
    if ($0 ~ /--resume-plan-tail/) resume_mentions++
    if ($0 ~ /snapshot-untracked\.sh" --output|\$SCRIPT_DIR\/persist-implement-run-flags\.sh|check-mid-run-dirty-tree\.sh" --mode checkpoint|create-branch\.sh" --branch|git-current-branch\.sh"|run-step1-plan-log\.sh"|write-tally\.sh"|tracking-issue-summary\.sh" .*upsert-summary|gh issue view "\$gh_issue_arg"|gh issue view "\$ISSUE_NUMBER"/) banned++
  }
  END {
    if (bootstrap_calls != 1) exit 10
    if (coder_literal < 1) exit 12
    if (banned != 0) exit 11
  }
' "$SKILL_MD" || step0_plan_structure_status=$?
case "$step0_plan_structure_status" in
  0) ;;
  10) fail "Step 0 bash blocks must contain exactly one implement-bootstrap.sh --up-to-phase coder call" ;;
  12) fail "Step 0 bash blocks must contain --up-to-phase coder literal" ;;
  11) fail "Step 0 bash blocks must not reintroduce absorbed plan-materialization helper calls" ;;
  *) fail "unexpected Step 0 structure check failure: $step0_plan_structure_status" ;;
esac
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
