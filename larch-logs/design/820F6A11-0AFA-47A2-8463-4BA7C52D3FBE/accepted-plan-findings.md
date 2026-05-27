### FINDING_1: Lint-fix-loop C1/C2 document and assert the wrong head-drift contract
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-harness-stub-contract, Codex-dyn-harness-stub-contract
- **Severity**: important
- **Concern**: C1/C2 claim defensive head-changed-after-dispatch branches reset the worktree to baseline and, in some places, assert the wrong status field. The cited runtime paths call fail_status directly, emitting LINT_FIX_STATUS=failed with FAILURE_REASON=head-changed-after-dispatch, and do not call reset_head_to_baseline except for forbidden-path handling. Literal implementation would create false SECURITY.md language and failing or misleading harness assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Drop the reset claim; align wording with lint-fix-loop.md (fail-closed, no coder-owned commit accepted) and existing case1c-1e harness expectations.
  - From Codex-Arch: Either add a minimal lint-fix-loop head-drift failure helper that restores baseline_branch/baseline_head before reporting head-changed-after-dispatch, or narrow C1/C2 to the existing fail-closed contract and remove the reset assertion/claim
  - From Cursor-Edge: For the minimum-change path, change C1/C2 to assert and document LINT_FIX_STATUS=failed with FAILURE_REASON=head-changed-after-dispatch, and remove the reset-to-baseline claim. Only add lint-fix-loop.sh reset behavior if this PR explicitly intends to change production semantics.
  - From Codex-Edge: For the minimum-change path, change C1/C2 to assert and document LINT_FIX_STATUS=failed with FAILURE_REASON=head-changed-after-dispatch, and remove the reset-to-baseline claim. Only add lint-fix-loop.sh reset behavior if this PR explicitly intends to change production semantics.
  - From Codex-Innovation: Minimum-change: remove the reset-to-baseline claim/assertions for these branches, or if that reset is required, add reset_head_to_baseline before head-changed-after-dispatch failures and test that behavior
  - From Cursor-Pragmatic: Append fail-closed language only (no coder-owned commit accepted); drop the reset claim, or add an explicit lint-fix-loop.sh reset in the same PR before documenting reset.
  - From Cursor-Requirements: Append fail-closed language only (no coder-owned commit accepted); drop the reset claim, or add an explicit lint-fix-loop.sh reset in the same PR before documenting reset.
  - From Codex-Pragmatic: Either add the minimal lint-fix-loop.sh change to reset to baseline before these head-changed-after-dispatch exits, or narrow the SECURITY.md/test assertions to the actual fail-closed-without-reset contract.
  - From Codex-Requirements: Revise C2 and the SECURITY.md sentence to assert LINT_FIX_STATUS=failed plus FAILURE_REASON=head-changed-after-dispatch
  - From Codex-Requirements: For the SIMPLE lane, remove the reset-to-baseline claim/assertion unless the feature explicitly requires adding reset_head_to_baseline before each head-changed-after-dispatch fail path
  - From Cursor-dyn-harness-stub-contract: Keep the minimum-change contract: assert rc 1, LINT_FIX_STATUS=failed, FAILURE_REASON=head-changed-after-dispatch, and no exported LINT_FIX_DELTA_PATHS_FILE
  - From Codex-dyn-harness-stub-contract: Keep the minimum-change contract: assert rc 1, LINT_FIX_STATUS=failed, FAILURE_REASON=head-changed-after-dispatch, and no exported LINT_FIX_DELTA_PATHS_FILE
  - From Cursor-dyn-harness-stub-contract: For this simple lane, remove the reset assertion and reset wording for head-changed branches; only add reset behavior if intentionally expanding scope beyond harness coverage
  - From Codex-dyn-harness-stub-contract: For this simple lane, remove the reset assertion and reset wording for head-changed branches; only add reset behavior if intentionally expanding scope beyond harness coverage


### FINDING_2: C2 duplicates existing lint-fix-loop defensive coverage and misses parent-mismatch
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Concern**: C2 proposes broad new defensive-branch fixtures even though nearby harness cases already cover detached HEAD, branch switch, history rewrite, merge commit, and dirty-baseline failures. The proposed sibling-branch fixture also would fail at the branch-name guard before exercising the intended current_parent != baseline_head guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Reuse the existing 1c/1d/1d5/1d6 cases for any new assertions; add only the truly missing empty-current-head case if that branch must be pinned
  - From Cursor-Edge: Reuse the existing cases where possible, add only a genuinely missing empty-current-head case if required, and if parent-mismatch coverage is still needed, make two sequential commits on the same branch so current_parent differs from baseline_head without tripping the branch-switch guard first.
  - From Codex-Edge: Reuse the existing cases where possible, add only a genuinely missing empty-current-head case if required, and if parent-mismatch coverage is still needed, make two sequential commits on the same branch so current_parent differs from baseline_head without tripping the branch-switch guard first.
  - From Cursor-Innovation: Remove Item C2 (and `scripts/test-lint-fix-loop.md` matrix expansion) from the plan; keep the single SECURITY.md sentence (C1) only
  - From Codex-Innovation: Replace that fixture with a same-branch two-commit advancement: baseline remains an ancestor, no second parent exists, and current_parent differs from baseline_head


### FINDING_3: Item A test strategy does not cover the changed verifier path
- **Reviewer(s)**: Cursor-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The plan claims existing make test-ship-pr coverage for Item A, but the described harness exercises run_per_job_local_fix_loop rather than the proposed _verify_failed_jobs_locally path. A TSV containing non-fixable/no-local-equivalent rows could still be skipped in verifier/vendor handling while current tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Revise the testing strategy to acknowledge the gap, or add one minimal vendor-path case (mixed TSV + per-job `head-changed` stub + assert `exit 3` / no push) instead of claiming existing `test-ship-pr` already covers Item A
  - From Codex-Requirements: Add a small sourced-function or vendor-path fixture that feeds _verify_failed_jobs_locally a TSV containing a non-fixable row and asserts exit 3 plus BAIL_REASON=ci-local-unfixable:<job>


### FINDING_4: D1 lacks post-force-push UNKNOWN-to-BEHIND regression coverage
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Planned G5/G6 tests cover initial empty-state recovery, but the proposed D1 behavior runs after force-push recovery when UNKNOWN resolves to BEHIND. Without a Q-style post-force-push case, the changed path could fall through to CI refresh or emit the wrong ERROR without failing the planned tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add or swap in one Q-style post_force_push_unknown_retry_behind case with GH_VIEW_FLIP_MERGE_STATE=BEHIND, pending second CI, and assertions for MERGE_RESULT=main_advanced, ERROR=, no merge commands, and no second post-push CI check
  - From Codex-Requirements: Add one Sub-test Q-style case where GH_VIEW_SECOND_MERGE_STATE=UNKNOWN flips to BEHIND after the force-push retry, asserting MERGE_RESULT=main_advanced, ERROR=, no merge command, and no post-retry CI check


### FINDING_5: D1/D2 insertion guidance can create duplicate UNKNOWN retry guards
- **Reviewer(s)**: Cursor-dyn-insertion-point-conflict, Codex-dyn-insertion-point-conflict
- **Severity**: important
- **Concern**: If implemented literally, D2 modifies the existing UNKNOWN retry call and D1 inserts another retry block after the same call. That can spend two retry budgets before checking BEHIND, while still reporting only one retry budget and adding avoidable latency and complexity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-insertion-point-conflict: Clarify D1 as either inserting only the BEHIND short-circuit between the existing retry guard and UNKNOWN error, or replacing scripts/merge-pr.sh:243-249 with one sequence: retry once, check BEHIND, then emit UNKNOWN error; do not add a second retry guard
  - From Codex-dyn-insertion-point-conflict: Clarify D1 as either inserting only the BEHIND short-circuit between the existing retry guard and UNKNOWN error, or replacing scripts/merge-pr.sh:243-249 with one sequence: retry once, check BEHIND, then emit UNKNOWN error; do not add a second retry guard

