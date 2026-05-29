# Review Round 1

- Mode: `diff`
- 16 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_1: Recovery PR lookup can delete a branch after transient probe failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After `gh pr create` retries fail, bare recovery `gh pr list`/`gh pr view` calls can fail transiently and look like “no PR exists,” causing remote branch deletion even if the PR was created server-side.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_10: Named block body edit failure drops captured stderr
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Wrapped `gh issue edit --body-file` failure in `scripts/named-block-write.sh` reads `ERR_TMP` instead of `edit_fail_file`, reporting an empty or stale error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Failed issue cleanup close failure drops captured stderr
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Wrapped close failure in `skills/issue/scripts/cleanup-failed-issue.sh` reads empty `ERR_TMP` instead of `close_fail_file`, producing blank `CLOSED=false ERROR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: PR body update failure drops captured stderr
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `scripts/gh-pr-body-update.sh` reports failure diagnostics from stdout while stderr is captured in a deleted fail file, so stderr-only `gh pr edit` failures produce empty `ERROR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: Design log publish lacks branch cleanup regression assertion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The hard create-failure test does not assert that the remote branch is deleted when PR recovery confirms no PR, allowing the non-fast-forward retry incident to regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Design log publish has unused retry output locals
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_push_out` and `_merge_out` are assigned but unused in `scripts/design-log-publish.sh`, adding maintenance noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_2: Tracking issue comment failure drops captured stderr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Wrapped `gh issue comment` failures in `scripts/tracking-issue-write.sh` read stale or empty `ERR_TMP` while the actual stderr is in `net_fail_file`, producing blank diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: PR body update lacks transient retry integration test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-gh-pr-body-update.sh` only stubs success, so the retry loop for wrapped `gh pr edit` is not exercised in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_27: test-lib-net documentation has stale tempdir prefix
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lib-net.md` documents a tempdir prefix that does not match the actual `mktemp` prefix in `scripts/test-lib-net.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Tracking issue rename failure reports stale diagnostics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Wrapped rename `gh issue edit` failures read stale `ERR_TMP` from a prior view instead of `rename_fail_file`, so operators see empty or unrelated errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_4: Tracking issue false-positive edit failure reports stale diagnostics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Wrapped mark-false-positive label/title edit failures read stale `ERR_TMP` instead of `mark_fail_file`, losing the actual GitHub error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: Clarify comment post failure drops captured stderr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Wrapped comment post failures in `scripts/clarify-comment-post.sh` read `ERR_TMP`, which the wrapper does not write, causing empty `ERROR=` output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: Clarify label mutation failure drops captured stderr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Wrapped add/remove label failures in `scripts/clarify-label.sh` read `ERR_TMP` instead of the per-call fail file, losing transport diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_7: Tracking issue summary upsert failure drops captured stderr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Wrapped comment and PATCH failures in `scripts/tracking-issue-summary.sh` read empty `err_tmp` instead of `comment_fail_file` or `patch_fail_file`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: Issue creation rollback close failure drops captured stderr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `rollback_orphan` in `skills/issue/scripts/create-one.sh` reads unused `rollback_err` instead of `rollback_fail_file`, so rollback close failures log empty diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Combine-issues close failure drops captured stderr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `.claude/skills/combine-issues/scripts/apply-combination.sh` sets `CLOSE_ERR` from `_WTR_OUT` while `gh` stderr lives in `close_fail_file`, producing empty warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.


