### FINDING_1: Stale postmerge comment filename
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh` still has one postmerge comment referring to `final-summary.md` under `IMPLEMENT_TMPDIR`, while adjacent comments were corrected to `summary-final.md`, creating contradictory maintenance guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: G7/Q2 test naming mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-merge-pr.md` refers to G7 while the harness subsection/assertions use Q2/Q2a-Q2d, making acceptance criteria harder to map to test output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Fragile awk slice in vendor verify test
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `vendor_verify_nonfixable_direct` slices `scripts/ship-pr.sh` between surrounding function names, so function reordering could make the test evaluate the wrong fragment or a narrowed fragment while still compiling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: Duplicated TSV class handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_verify_failed_jobs_locally` and `run_per_job_local_fix_loop` duplicate the TSV class case block, increasing the chance that future class-token changes are applied to one path but not the other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: G7 ERROR assertion is too weak
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: G7 checks for `ERROR=` as a substring, so it could pass even if `MERGE_RESULT=main_advanced` is emitted with a non-empty `ERROR` value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: G7 lacks pr view call-count assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: G7 does not assert the `gh pr view` call count, so the post-force-push UNKNOWN retry sequence could be skipped while stubs still produce `main_advanced` and one `pr checks` call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Repeated BEHIND short-circuit blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/merge-pr.sh` repeats BEHIND short-circuit logic, increasing maintenance cost when changing the `main_advanced` contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Missing post-force-push empty-state recovery test
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: There is no test for a post-force-push empty merge state recovering to BEHIND, so that transient empty post-push path could still fall through to error while initial empty recovery is covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Mixed fixable and non-fixable TSV coverage gap
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The vendor verify test covers all-non-fixable TSV rows but not a mixed fixable plus non-fixable TSV, leaving weaker regression coverage for the path where fixable work runs and the consolidated non-fixable bail must still block push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] Mixed TSV runs fixable work before failing closed
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: When fixable and non-fixable rows coexist, local fix work still runs before the consolidated bail; this matches the current plan but can waste work on doomed runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] job token path interpolation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `job_token` is interpolated into per-job paths under `IMPLEMENT_TMPDIR`; the reviewer notes existing allowlist mitigation and treats this as pre-existing, not introduced by the change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] merge state embedded in ERROR
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `ERROR` embeds `MERGE_STATE` from `gh`/`jq`; the reviewer notes GitHub enum constraints and treats this as a pre-existing adjacent-path pattern, not a new regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Future return-3 refactor could run vendor work
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `run_evaluate_failure` does not explicitly treat `run_per_job_local_fix_loop` rc `3` as terminal before the vendor branch; today `exit 3` terminates the script, but a future change to `return 3` could reintroduce wasted vendor work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
