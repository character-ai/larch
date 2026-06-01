#!/usr/bin/env bash
# Structural regression test for /implement SKILL.md + larch-log migration.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
# shellcheck source=scripts/lib-p3119-fence-absence.sh
source "$REPO_ROOT/scripts/lib-p3119-fence-absence.sh"
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
grep -Fq 'stall-recovery-report.sh clear-stall' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must delegate stall clearing through stall-recovery-report.sh clear-stall"
grep -Fq 'stall-recovery-report.sh seed-terminal-state' "$STALL_RECOVERY_MD" \
  || fail "stall-recovery.md must delegate terminal seeding through stall-recovery-report.sh seed-terminal-state"
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
{ grep -Fq -- '--workflow-path HARD' "$REPO_ROOT/scripts/implement-bootstrap.sh" || \
  grep -Fq 'persist_run_flags HARD' "$REPO_ROOT/scripts/implement-bootstrap.sh"; } \
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
  in_step && /<!-- step:/ { in_step = 0; in_bash = 0 }
  in_step && /^```(bash|sh|shell)[[:space:]]*$/ { in_bash = 1; next }
  in_step && in_bash && /^```[[:space:]]*$/ { in_bash = 0; next }
  in_step && /step-18b-final-report\.sh/ && /--implement-tmpdir "\$IMPLEMENT_TMPDIR"/ { wrapper = 1 }
  in_step && /EMIT_BODY=\$\(printf/ { emit_parse = 1 }
  in_step && /WFR_RC=\$\(printf/ { wfr_parse = 1 }
  in_step && /STEP17_EMITTED_PRESENT=\$\(printf/ { step17_parse = 1 }
  in_step && in_bash && /write-final-report\.sh/ && /--print-stdout/ { bad_print = 1 }
  in_step && /EMIT_BODY=true/ && /WFR_RC=0/ && /summary-final\.md/ { emit_guard = 1 }
  END {
    if (!wrapper || !emit_parse || !wfr_parse || !step17_parse || bad_print || !emit_guard) exit 1
    exit 0
  }
' "$SKILL_MD" || step18_status=$?
[[ "$step18_status" == "0" ]] || fail "SKILL.md Step 18 must delegate to step-18b-final-report.sh and gate orchestrator emit on EMIT_BODY=true with WFR_RC=0"

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
grep -Fq 'NEVER set `OOS_PENDING=false` without a passing `oos-disposition-checkpoint.sh` invocation' "$SKILL_MD" \
  || fail "SKILL.md must retain NEVER #18 checkpoint-before-clear pin (OOS_PENDING vs oos-disposition-checkpoint.sh)"
# shellcheck disable=SC2016
grep -Fq '${CLAUDE_PLUGIN_ROOT}/skills/implement/scripts/oos-disposition-checkpoint.sh' "$SKILL_MD" \
  || fail "SKILL.md Step 8+ must reference oos-disposition-checkpoint.sh"

# Folded Step 0 / admission structural pins (fix-issue removal; Step 0 + Preflight admission)
grep -Fq 'scripts/implement-admission.sh' "$SKILL_MD" \
  || fail "SKILL.md must reference scripts/implement-admission.sh"
grep -Fq '1. **Admission gate**' "$SKILL_MD" \
  || fail "SKILL.md Preflight must contain numbered Admission gate step"
grep -Fq '**Preflight — admission gate known limitation (D3)**' "$SKILL_MD" \
  || fail "SKILL.md must document admission gate fail-open limitation (D3)"
# shellcheck disable=SC2016
grep -Fq '6. **On `AUDIT=pass` or emergency-bypassed `AUDIT=refuse` — semantic materiality (comment-only)**' "$SKILL_MD" \
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
[ -f "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" ] \
  || fail "scripts/implement-bootstrap-invoke.sh must exist"
[ -f "$REPO_ROOT/scripts/implement-bootstrap-invoke.md" ] \
  || fail "scripts/implement-bootstrap-invoke.md must exist"
grep -Fq 'implement-bootstrap-invoke.sh --mode initial' "$SKILL_MD" \
  || fail "SKILL.md must call implement-bootstrap-invoke.sh --mode initial"
if [ "$(grep -oF 'implement-bootstrap-invoke.sh --mode initial' "$SKILL_MD" 2>/dev/null | wc -l | tr -d ' ')" -lt 1 ]; then
  fail "SKILL.md must reference implement-bootstrap-invoke.sh --mode initial"
fi
if [ "$(grep -oF 'implement-bootstrap-invoke.sh --mode resume' "$SKILL_MD" 2>/dev/null | wc -l | tr -d ' ')" -lt 1 ]; then
  fail "SKILL.md must call implement-bootstrap-invoke.sh --mode resume (dirty-tree)"
fi
grep -Fq 'implement-bootstrap-invoke.sh --mode initial' "$SKILL_MD" \
  || fail "Protocol Execution Directive must name implement-bootstrap-invoke.sh --mode initial"
grep -Fq '_ib_preflight=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_preflight argv array"
grep -Fq '_ib_emergency=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_emergency argv array"
true
grep -Fq -- '--resume-plan-tail' "$REPO_ROOT/scripts/implement-bootstrap.md" \
  || fail "implement-bootstrap.md must document --resume-plan-tail"
grep -Fq -- '--resume-plan-tail' "$SKILL_MD" \
  || fail "SKILL.md must retain dirty-tree resume-tail routing"
grep -Fq '## Step 0 — Session Setup' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 0 Session Setup heading"
grep -Fq "**⚠ Foreground required — do NOT set \`run_in_background: true\`.**" "$SKILL_MD" \
  || fail "SKILL.md must retain the Step 0 foreground-required warning"
{ grep -Fq 'Dirty-tree recovery bootstrap fence:' "$SKILL_MD" || \
  grep -Fq 'Step 0 dirty-tree recovery gate:' "$SKILL_MD"; } \
  || fail "SKILL.md must retain the dirty-tree recovery bootstrap fence"
grep -Fq 'Resume-tail idempotency' "$REPO_ROOT/scripts/implement-bootstrap.md" \
  || fail "implement-bootstrap.md must document resume-tail idempotency invariant"
grep -Fq 'the first pass bails at this checkpoint' "$REPO_ROOT/scripts/implement-bootstrap.md" \
  || fail "implement-bootstrap.md must pin the dirty-tree first-pass-bail-before-helpers invariant"
grep -Fq '_ib_caller_env=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_caller_env argv assembly"
grep -Fq '_ib_issue=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_issue argv assembly"
grep -Fq '_ib_fork=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_fork argv assembly"
grep -Fq '_ib_run_id=()' "$SKILL_MD" \
  && fail "SKILL.md must not retain inline _ib_run_id argv assembly"
grep -Fq '_ib_run_bootstrap() {' "$SKILL_MD" \
  && fail "SKILL.md must not retain _ib_run_bootstrap helper"
grep -Fq '_ib_parse_bootstrap_out() {' "$SKILL_MD" \
  && fail "SKILL.md must not retain dead _ib_parse_bootstrap_out helper"
grep -Fq '_ib_run_bootstrap --resume-plan-tail' "$SKILL_MD" \
  && fail "SKILL.md must not call _ib_run_bootstrap --resume-plan-tail"
grep -Fq '_ib_parse_bootstrap_out' "$SKILL_MD" \
  && fail "SKILL.md must not reference _ib_parse_bootstrap_out"
if grep -Fq 'not-yet-implemented-phase-' "$SKILL_MD"; then
  fail "SKILL.md must not reintroduce not-yet-implemented phase bail placeholders"
fi
# shellcheck disable=SC2016 # literal source text, not shell.
grep -Fq 'larch_err "→ step0: coder=${coder}"' "$REPO_ROOT/scripts/implement-bootstrap.sh" \
  || fail "implement-bootstrap.sh must retain the coder breadcrumb literal"
grep -Fq 'Review/fix and other fixer lanes remain Codex-first' "$REPO_ROOT/SECURITY.md" \
  || fail "SECURITY.md must document Codex-first fixer adjacency"
grep -Fq "Operators who want Codex on \`/implement\` can pin it explicitly with \`--coder=codex\`." "$REPO_ROOT/SECURITY.md" \
  || fail "SECURITY.md must document explicit --coder=codex pinning"
# shellcheck disable=SC2016 # literal removed-helper pin.
grep -Fq '_ib_target_issue="${TARGET_ISSUE_NUMBER:-${ISSUE_NUMBER:-}}"' "$SKILL_MD" \
  && fail "SKILL.md must not retain _ib_target_issue helper"
if [ "$(grep -oF '_ib_rc' "$SKILL_MD" 2>/dev/null | wc -l | tr -d ' ')" -ge 1 ]; then
  fail "SKILL.md must not retain _ib_rc (use _inv_rc)"
fi
if [ "$(grep -oF '_inv_rc' "$SKILL_MD" 2>/dev/null | wc -l | tr -d ' ')" -lt 2 ]; then
  fail "SKILL.md must use _inv_rc at initial Step 0 and dirty-tree recovery"
fi
if [ "$(grep -cF '_inv_rc=$?' "$SKILL_MD" || true)" -lt 2 ]; then
  fail "SKILL.md must capture _inv_rc after each wrapper call"
fi
step0_wrapper_fence_status=0
awk '
  /<!-- step:0/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0; in_bash = 0 }
  in_step && /^```(bash|sh|shell)[[:space:]]*$/ { in_bash = 1; next }
  in_step && in_bash && /^```[[:space:]]*$/ { in_bash = 0; next }
  in_step && in_bash && /^[[:space:]]*#/ { prev2 = prev1; prev1 = $0; next }
  in_step && in_bash && /^[[:space:]]*_inv_out=\$\(.+implement-bootstrap-invoke\.sh" --mode (initial|resume)/ {
    mode = ($0 ~ /--mode initial/) ? "initial" : "resume"
    if (prev1 != "set +e") exit 20
    getline rc_line
    if (rc_line != "_inv_rc=$?") exit 21
    getline sete_line
    if (sete_line != "set -e") exit 22
    seen[mode]++
    prev2 = prev1
    prev1 = sete_line
    next
  }
  in_step && in_bash {
    prev2 = prev1
    prev1 = $0
  }
  END {
    if (seen["initial"] < 1) exit 23
    if (seen["resume"] < 1) exit 24
  }
' "$SKILL_MD" || step0_wrapper_fence_status=$?
case "$step0_wrapper_fence_status" in
  0) ;;
  20) fail "each implement-bootstrap-invoke.sh call must be immediately preceded by set +e" ;;
  21) fail "each implement-bootstrap-invoke.sh call must be immediately followed by _inv_rc=\$?" ;;
  22) fail "each implement-bootstrap-invoke.sh _inv_rc capture must be immediately followed by set -e" ;;
  23) fail "Step 0 wrapper fence check did not see initial invocation" ;;
  24) fail "Step 0 wrapper fence check did not see resume invocation" ;;
  *) fail "unexpected Step 0 wrapper fence check failure: $step0_wrapper_fence_status" ;;
esac
if [ "$(grep -cE '^[[:space:]]*_inv_out=\$\("\$\{CLAUDE_PLUGIN_ROOT\}/scripts/implement-bootstrap-invoke\.sh"' "$SKILL_MD" || true)" -lt 2 ]; then
  fail "SKILL.md must contain at least two uncommented _inv_out= implement-bootstrap-invoke.sh call sites"
fi
[ -f "$REPO_ROOT/scripts/parse-bootstrap-routing-envelope.sh" ] \
  || fail "scripts/parse-bootstrap-routing-envelope.sh must exist"
[ -f "$REPO_ROOT/scripts/parse-bootstrap-routing-envelope.md" ] \
  || fail "scripts/parse-bootstrap-routing-envelope.md must exist"
grep -Fq 'parse-bootstrap-routing-envelope.sh' "$SKILL_MD" \
  || fail "SKILL.md must source parse-bootstrap-routing-envelope.sh"
# shellcheck disable=SC2016 # literal source text, not shell.
if [ "$(grep -cF '. "${CLAUDE_PLUGIN_ROOT}/scripts/parse-bootstrap-routing-envelope.sh"' "$SKILL_MD" || true)" -ne 2 ]; then
  fail "SKILL.md must source parse-bootstrap-routing-envelope.sh exactly twice (initial + resume)"
fi
grep -Fq 'parse-bootstrap-routing-envelope.sh" --preserve-coder' "$SKILL_MD" \
  || fail "SKILL.md dirty-tree resume must source parse-bootstrap-routing-envelope.sh --preserve-coder"
grep -Fq '_inv_routing_keys=' "$SKILL_MD" \
  && fail "SKILL.md must not duplicate _inv_routing_keys (owned by parse-bootstrap-routing-envelope.sh)"
grep -Fq '_inv_apply_routing_line()' "$SKILL_MD" \
  && fail "SKILL.md must not define _inv_apply_routing_line (owned by parse-bootstrap-routing-envelope.sh)"
grep -Fq '_inv_apply_routing_line_if_empty()' "$SKILL_MD" \
  && fail "SKILL.md must not define _inv_apply_routing_line_if_empty (owned by parse-bootstrap-routing-envelope.sh)"
# shellcheck disable=SC2016 # literal source text, not shell.
if [ "$(grep -cF 'if [ "$_inv_rc" -ne 0 ]; then' "$SKILL_MD" || true)" -lt 2 ]; then
  fail "SKILL.md must exit on non-zero wrapper rc before routing parse (both call sites)"
fi
grep -Fq 'unset IMPLEMENT_BAIL_REASON STALL_TRACKING PLAN_FILE coder coder_fallback' "$REPO_ROOT/scripts/parse-bootstrap-routing-envelope.sh" \
  || fail "parse-bootstrap-routing-envelope.sh initial unset must include coder coder_fallback"
grep -Fq 'unset IMPLEMENT_BAIL_REASON STALL_TRACKING PLAN_FILE REPO_UNAVAILABLE' "$REPO_ROOT/scripts/parse-bootstrap-routing-envelope.sh" \
  || fail "parse-bootstrap-routing-envelope.sh resume unset must omit coder coder_fallback"
grep -Fq '_ib_kv_scan()' "$SKILL_MD" \
  && fail "SKILL.md must not retain _ib_kv_scan helper"
grep -Fq '_ib_handle_bootstrap_exit2()' "$SKILL_MD" \
  && fail "SKILL.md must not retain _ib_handle_bootstrap_exit2 helper"
expected_routing_keys='IMPLEMENT_TMPDIR IMPLEMENT_BAIL_REASON STALL_TRACKING PLAN_FILE coder coder_fallback REPO_UNAVAILABLE DEFERRED ISSUE_NUMBER REPO CODEX_PRESENT CURSOR_PRESENT CODEX_BINARY_FOUND CURSOR_BINARY_FOUND codex_available cursor_available RUN_ID BRANCH_NAME BRANCH_ACTION'
parse_keys=$(awk -F"'" '/^_inv_routing_keys=/ {print $2; exit}' "$REPO_ROOT/scripts/parse-bootstrap-routing-envelope.sh")
invoke_keys=$(awk -F"'" '/^_inv_routing_keys=/ {print $2; exit}' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh")
if [ "$parse_keys" != "$expected_routing_keys" ] || [ "$invoke_keys" != "$expected_routing_keys" ]; then
  fail "parse-bootstrap-routing-envelope.sh and implement-bootstrap-invoke.sh _inv_routing_keys must match canonical list"
fi
if [ "$parse_keys" != "$invoke_keys" ]; then
  fail "parse-bootstrap-routing-envelope.sh and implement-bootstrap-invoke.sh _inv_routing_keys literals must be identical"
fi
grep -Fq "BRANCH_NAME=*) BRANCH_NAME=\${_ib_tok#BRANCH_NAME=} ;;" "$SKILL_MD" \
  && fail "SKILL.md must not retain BRANCH_NAME _ib_kv_scan case arm"
grep -Fq "BRANCH_ACTION=*) BRANCH_ACTION=\${_ib_tok#BRANCH_ACTION=} ;;" "$SKILL_MD" \
  && fail "SKILL.md must not retain BRANCH_ACTION _ib_kv_scan case arm"
grep -Fq "PLAN_FILE=*) PLAN_FILE=\${_ib_tok#PLAN_FILE=} ;;" "$SKILL_MD" \
  && fail "SKILL.md must not retain PLAN_FILE _ib_kv_scan case arm"
grep -Fq "coder=*) coder=\${_ib_tok#coder=} ;;" "$SKILL_MD" \
  && fail "SKILL.md must not retain coder _ib_kv_scan case arm"
grep -Fq 'BRANCH_NAME' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must include BRANCH_NAME in routing envelope key set"
grep -Fq 'PLAN_FILE' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must include PLAN_FILE in routing envelope key set"
grep -Fq 'coder_fallback' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must include coder_fallback in routing envelope key set"
grep -Fq 'copy-plan)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain copy-plan exit-2 handler"
grep -Fq 'gh-issue-view)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain gh-issue-view exit-2 handler"
grep -Fq 'create-branch)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain create-branch exit-2 handler"
grep -Fq 'write-session-env)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain write-session-env exit-2 handler"
grep -Fq 'emergency-bypass-log)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain emergency-bypass-log exit-2 handler"
grep -Fq '*)' "$REPO_ROOT/scripts/implement-bootstrap-invoke.sh" \
  || fail "implement-bootstrap-invoke.sh must retain default exit-2 handler"
# shellcheck disable=SC2016
grep -Fq 'run-step2-dispatch.sh` always passes `--plan-file "$IMPLEMENT_TMPDIR/plan.txt"`' "$SKILL_MD" \
  || fail "SKILL.md must retain Step 2 conventional plan-file wording"
# shellcheck disable=SC2016
grep -Fq 'launcher must fail closed if session-env later says `CURSOR_PRESENT!=true`' "$SKILL_MD" \
  || fail "SKILL.md must document fail-closed cursor selection drift handling"

step0_plan_structure_status=0
awk '
  /<!-- step:0/ { in_step = 1; next }
  in_step && /<!-- step:/ { in_step = 0; in_bash = 0 }
  in_step && /^```(bash|sh|shell)[[:space:]]*$/ { in_bash = 1; next }
  in_step && in_bash && /^```[[:space:]]*$/ { in_bash = 0; next }
  in_step && in_bash {
    if ($0 ~ /implement-bootstrap\.sh/) direct_bootstrap++
    if ($0 ~ /--up-to-phase coder/) coder_literal++
    if ($0 ~ /--resume-plan-tail/) resume_literal++
    if ($0 ~ /^[[:space:]]*#/) next
    if ($0 ~ /^[[:space:]]*_inv_out=\$\(.+implement-bootstrap-invoke\.sh" --mode initial/) mode_initial++
    if ($0 ~ /^[[:space:]]*_inv_out=\$\(.+implement-bootstrap-invoke\.sh" --mode resume/) mode_resume++
    if ($0 ~ /snapshot-untracked\.sh" --output|\$SCRIPT_DIR\/persist-implement-run-flags\.sh|check-mid-run-dirty-tree\.sh" --mode checkpoint|create-branch\.sh" --branch|git-current-branch\.sh"|run-step1-plan-log\.sh"|write-tally\.sh"|tracking-issue-summary\.sh" .*upsert-summary|gh issue view "\$gh_issue_arg"|gh issue view "\$ISSUE_NUMBER"/) banned++
  }
  END {
    if (direct_bootstrap != 0) exit 10
    if (coder_literal != 0) exit 12
    if (resume_literal != 0) exit 13
    if (mode_initial < 1) exit 14
    if (mode_resume < 1) exit 15
    if (banned != 0) exit 11
  }
' "$SKILL_MD" || step0_plan_structure_status=$?
case "$step0_plan_structure_status" in
  0) ;;
  10) fail "Step 0 bash blocks must not call implement-bootstrap.sh directly" ;;
  12) fail "Step 0 bash blocks must not contain --up-to-phase coder literal (wrapper-owned)" ;;
  13) fail "Step 0 bash blocks must not contain --resume-plan-tail literal (wrapper-owned)" ;;
  14) fail "Step 0 bash blocks must call implement-bootstrap-invoke.sh --mode initial" ;;
  15) fail "Step 0 bash blocks must call implement-bootstrap-invoke.sh --mode resume" ;;
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

# Stage 4 (#3119): Family-B fence shape must stay absent from implement orchestrator docs.
assert_p3119_family_b_fence_absent "$SKILL_MD" "SKILL.md" ship-pr-invocation
assert_p3119_family_b_fence_absent "$STALL_RECOVERY_MD" "stall-recovery.md"
assert_p3119_family_b_fence_absent "$REFS_DIR/rebase-rebump-subprocedure.md" "rebase-rebump-subprocedure.md"
grep -Fq "treat the foreground Bash tool exit code as \`writer_rc\`" "$SKILL_MD" \
  || fail "(3119) SKILL.md Step 8+ must pin foreground writer_rc routing (post ship-pr return)"
grep -Fq "Treat the foreground Bash tool exit code as \`writer_rc\`" "$SKILL_MD" \
  || fail "(3119) SKILL.md Exit 4 must pin foreground writer_rc routing"
grep -Fq "treat the foreground Bash tool exit code as \`writer_rc\`" "$STALL_RECOVERY_MD" \
  || fail "(3119) stall-recovery.md step8-shippr must pin foreground writer_rc routing"

echo "All assertions passed."
