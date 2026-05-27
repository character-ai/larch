### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: SECURITY.md:204 (proposed append)
- **Concern**: Proposed SECURITY sentence claims post-dispatch defensive branches reset the working tree to baseline_head before reporting head-changed-after-dispatch. Scenario: lint-fix-loop.sh fail_status paths at 374-390 exit with LINT_FIX_STATUS=failed and FAILURE_REASON=head-changed-after-dispatch without calling reset_head_to_baseline; only forbidden-path handling resets (396-399). Published SECURITY text would misstate runtime behavior.
- **Proposed resolution**: Drop the reset claim; align wording with lint-fix-loop.md (fail-closed, no coder-owned commit accepted) and existing case1c-1e harness expectations.

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:31-35,373-390
- **Concern**: Plan claims and tests reset-to-baseline behavior for head-drift failures, but the runtime fail_status paths exit without any reset. Scenario: The proposed C2 reset assertions fail, and the SECURITY.md C1 sentence would overstate the post-dispatch safety invariant while detached, non-ancestor, merge-commit, or branch-switch HEAD remains checked out after failure
- **Proposed resolution**: Either add a minimal lint-fix-loop head-drift failure helper that restores baseline_branch/baseline_head before reporting head-changed-after-dispatch, or narrow C1/C2 to the existing fail-closed contract and remove the reset assertion/claim

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: scripts/test-lint-fix-loop.sh:530-608
- **Concern**: C2 proposes adding broad new defensive-branch fixtures even though the harness already covers detached HEAD, branch switch, amended-history/non-ancestor, and merge-commit cases. Scenario: This duplicates 60-120 lines of setup in a SIMPLE lane and increases maintenance without materially expanding coverage for those branches
- **Proposed resolution**: Reuse the existing 1c/1d/1d5/1d6 cases for any new assertions; add only the truly missing empty-current-head case if that branch must be pinned

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:148 and plan.txt:156; scripts/lint-fix-loop.sh:31-35,373-390
- **Concern**: C1/C2 specify the wrong lint-fix-loop failure contract. Scenario: The helper emits LINT_FIX_STATUS=failed plus FAILURE_REASON=head-changed-after-dispatch, and the HEAD-validation fail_status paths do not reset to baseline before exiting. Implementing the plan literally creates failing harness assertions and a SECURITY.md sentence that documents behavior callers will not observe.
- **Proposed resolution**: For the minimum-change path, change C1/C2 to assert and document LINT_FIX_STATUS=failed with FAILURE_REASON=head-changed-after-dispatch, and remove the reset-to-baseline claim. Only add lint-fix-loop.sh reset behavior if this PR explicitly intends to change production semantics.

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge, Codex-Edge
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: plan.txt:141-148; scripts/test-lint-fix-loop.sh:530-608
- **Concern**: C2 duplicates existing defensive-branch coverage and still misses the named parent-mismatch branch. Scenario: The current harness already has detached, branch-switch, amended-history-rewrite, and merge-commit cases. Adding another 60-120 lines is scope creep, and the proposed sibling-branch simulation for current_parent != baseline_head will fail earlier at the symbolic-branch check rather than exercising the parent check at scripts/lint-fix-loop.sh:389-390.
- **Proposed resolution**: Reuse the existing cases where possible, add only a genuinely missing empty-current-head case if required, and if parent-mismatch coverage is still needed, make two sequential commits on the same branch so current_parent differs from baseline_head without tripping the branch-switch guard first.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/test-lint-fix-loop.sh:530-629
- **Concern**: Item C2 proposes ~60-120 lines of new defensive-branch fixtures but cases 1c/1d/1d.5/1d.6/1e already exercise detached HEAD, branch switch, history rewrite, merge commit, and dirty-baseline failures with `FAILURE_REASON=head-changed-after-dispatch`. Scenario: Duplicate harness work inflates the ~180-line PR without new behavioral coverage; only SECURITY.md C1 and doc sync are needed for the stated invariant
- **Proposed resolution**: Remove Item C2 (and `scripts/test-lint-fix-loop.md` matrix expansion) from the plan; keep the single SECURITY.md sentence (C1) only

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:198-201
- **Concern**: Testing strategy claims `make test-ship-pr` covers Item A, but no fixture targets `_verify_failed_jobs_locally` after `run_per_job_local_fix_loop` returns 2 while the failed-jobs TSV still has `no-local-equivalent` rows (e.g. gitleaks) that the old `[[ "$class" == "fixable" ]] || continue` silently skips. Scenario: `ci_per_job_unfixable` bails in `run_per_job_local_fix_loop` before vendor; the vendor→`_verify` push bypass (early `return 2` with unfixable still populated only at parse) stays untested and the strategy overstates regression coverage
- **Proposed resolution**: Revise the testing strategy to acknowledge the gap, or add one minimal vendor-path case (mixed TSV + per-job `head-changed` stub + assert `exit 3` / no push) instead of claiming existing `test-ship-pr` already covers Item A

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/lint-fix-loop.sh:31-34,373-390
- **Concern**: Plan documents and tests reset-on-head-change, but the proposed changes do not implement that reset. Scenario: The head-validation branches call fail_status directly; a detached HEAD, branch switch, non-ancestor, or merge-commit fixer can leave the repo away from baseline while C2 reset assertions fail and SECURITY.md claims a false invariant
- **Proposed resolution**: Minimum-change: remove the reset-to-baseline claim/assertions for these branches, or if that reset is required, add reset_head_to_baseline before head-changed-after-dispatch failures and test that behavior

### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:377-390
- **Concern**: C2's non-linear branch-switch fixture does not exercise the intended parent-mismatch guard. Scenario: A sibling-branch fixture fails at the branch-name check before reaching current_parent != baseline_head, so it duplicates existing branch-switch coverage and leaves the line 389 parent guard unpinned
- **Proposed resolution**: Replace that fixture with a same-branch two-commit advancement: baseline remains an ancestor, no second parent exists, and current_parent differs from baseline_head

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/merge-pr.sh:243-251, scripts/test-merge-pr.sh:607-640
- **Concern**: D1's changed post-force-push UNKNOWN-to-BEHIND path is not covered by the proposed G5/G6 tests. Scenario: G5/G6 exercise initial empty-state recovery, while the new code runs only after flush force-push recovery; omitting the new BEHIND check could still let post-push BEHIND fall through to CI refresh or a non-empty ERROR without failing those tests
- **Proposed resolution**: Add or swap in one Q-style post_force_push_unknown_retry_behind case with GH_VIEW_FLIP_MERGE_STATE=BEHIND, pending second CI, and assertions for MERGE_RESULT=main_advanced, ERROR=, no merge commands, and no second post-push CI check

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: SECURITY.md:204 (proposed C1 append)
- **Concern**: Proposed sentence claims working tree is reset to baseline_head on head-changed-after-dispatch. Scenario: scripts/lint-fix-loop.sh:374-390 call fail_status without reset_head_to_baseline; only forbidden-path violations reset (lines 396-398). Doc would misstate the security invariant.
- **Proposed resolution**: Append fail-closed language only (no coder-owned commit accepted); drop the reset claim, or add an explicit lint-fix-loop.sh reset in the same PR before documenting reset.

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:373-390
- **Concern**: The plan adds SECURITY.md text and tests claiming defensive HEAD-validation failures reset the worktree to baseline, but it does not update the defensive fail_status paths to perform that reset.. Scenario: Detached HEAD, non-ancestor, merge-commit, or multi-commit advancement currently exits via fail_status without calling reset_head_to_baseline, leaving the repository on the external fixer-created HEAD while the proposed docs/tests assert reset-to-baseline behavior.
- **Proposed resolution**: Either add the minimal lint-fix-loop.sh change to reset to baseline before these head-changed-after-dispatch exits, or narrow the SECURITY.md/test assertions to the actual fail-closed-without-reset contract.

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:31-34; <TMPDIR>/plan.txt:148
- **Concern**: C2 asserts the wrong lint-fix-loop status contract. Scenario: The plan says new cases should assert LINT_FIX_STATUS=head-changed-after-dispatch, but fail_status emits LINT_FIX_STATUS=failed and FAILURE_REASON=head-changed-after-dispatch, so the proposed harness would either fail or encode a non-existent contract
- **Proposed resolution**: Revise C2 and the SECURITY.md sentence to assert LINT_FIX_STATUS=failed plus FAILURE_REASON=head-changed-after-dispatch

### FINDING_14:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/lint-fix-loop.sh:373-390; <TMPDIR>/plan.txt:148-156
- **Concern**: C1/C2 claim reset-to-baseline for HEAD-validation branches without a matching implementation. Scenario: The current defensive branches call fail_status immediately and only forbidden-path handling calls reset_head_to_baseline, so the proposed SECURITY.md invariant and reset assertions describe behavior the plan does not implement
- **Proposed resolution**: For the SIMPLE lane, remove the reset-to-baseline claim/assertion unless the feature explicitly requires adding reset_head_to_baseline before each head-changed-after-dispatch fail path

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-merge-pr.sh:607-640; <TMPDIR>/plan.txt:90-110
- **Concern**: D1 lacks a post-force-push UNKNOWN to BEHIND regression test. Scenario: The only planned new merge-pr tests cover initial empty-state recovery, while the proposed code change specifically preserves empty ERROR and skips CI when post-force-push UNKNOWN resolves to BEHIND
- **Proposed resolution**: Add one Sub-test Q-style case where GH_VIEW_SECOND_MERGE_STATE=UNKNOWN flips to BEHIND after the force-push retry, asserting MERGE_RESULT=main_advanced, ERROR=, no merge command, and no post-retry CI check

### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-ship-pr.sh:3190-3233; <TMPDIR>/plan.txt:198-202
- **Concern**: Item A testing is claimed but not specified for the changed verifier path. Scenario: The existing unfixable job harness exercises run_per_job_local_fix_loop, not the proposed _verify_failed_jobs_locally change, so make test-ship-pr could pass while the vendor verification path still skips non-fixable rows
- **Proposed resolution**: Add a small sourced-function or vendor-path fixture that feeds _verify_failed_jobs_locally a TSV containing a non-fixable row and asserts exit 3 plus BAIL_REASON=ci-local-unfixable:<job>

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-insertion-point-conflict, Codex-dyn-insertion-point-conflict
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/merge-pr.sh:240-249
- **Concern**: D1/D2 conflict leaves two UNKNOWN retry guards if implemented literally: D2 changes the existing line 244 call, then D1 says to insert a block after that same call whose first branch calls retry_pr_info_unknown_recovery again before the BEHIND check. Scenario: If post-force-push MERGE_STATE remains empty or UNKNOWN after the first 3-retry budget, control flow retries a second 3-retry budget before checking BEHIND; the error still reports only 3 retries, and the plan adds unnecessary retry latency/complexity
- **Proposed resolution**: Clarify D1 as either inserting only the BEHIND short-circuit between the existing retry guard and UNKNOWN error, or replacing scripts/merge-pr.sh:243-249 with one sequence: retry once, check BEHIND, then emit UNKNOWN error; do not add a second retry guard

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-harness-stub-contract, Codex-dyn-harness-stub-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:31-34,373-390
- **Concern**: C2 proposes asserting LINT_FIX_STATUS=head-changed-after-dispatch, but the helper emits LINT_FIX_STATUS=failed and puts head-changed-after-dispatch in FAILURE_REASON. Scenario: Those new cases fail despite exercising the intended fail-closed branches; existing nearby cases assert the current contract at scripts/test-lint-fix-loop.sh:543-548,563-568,603-608
- **Proposed resolution**: Keep the minimum-change contract: assert rc 1, LINT_FIX_STATUS=failed, FAILURE_REASON=head-changed-after-dispatch, and no exported LINT_FIX_DELTA_PATHS_FILE

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-harness-stub-contract, Codex-dyn-harness-stub-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-fix-loop.sh:146-155,373-390
- **Concern**: The plan says the head-changed defensive branches reset the working tree to baseline, but those branches call fail_status directly and never call reset_head_to_baseline. Scenario: Proposed reset-to-baseline assertions and the SECURITY.md sentence would be false; detached, sibling-branch, and merge-commit fixtures remain at the post-dispatch HEAD after exit
- **Proposed resolution**: For this simple lane, remove the reset assertion and reset wording for head-changed branches; only add reset behavior if intentionally expanding scope beyond harness coverage
