### FINDING_1: correctness: design-log cleanup deletes branch after inconclusive PR list
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Cleanup deletes the pushed remote branch when `gh pr create` fails and `PR_NUM` remains empty, even if the follow-up `gh pr list` failed or was inconclusive. This can delete `origin/$WT_BRANCH` while a PR may already exist from a lost create response.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: code-quality: unrelated awk multibyte regex lint feature bundled with retry fix
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: The diff bundles an unrelated `lint-awk-multibyte-regex` feature with the transient retry fix, forcing reviewers to validate independent behavior changes together.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: risk-integration: nested merge retries compound latency
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `ship_pr_with_transient_retry` retries `merge-pr.sh`, while `merge-pr.sh` also retries `gh pr merge`, multiplying attempts and sleeps during sustained GitHub outages.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: code-quality: create-pr push retry diverges from git-push.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `create-pr.sh` implements push retry behavior directly instead of reusing `git-push.sh`, creating inconsistent backoff and retry behavior for the same operation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: code-quality: duplicated ship-pr retry wrapper in test harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-lib-net.sh` duplicates `ship_pr_with_transient_retry`, so future wrapper edits may not be reflected in regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: correctness: design-log test title contradicts branch-deletion assertions
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The list-probe failure test title says the branch should be kept, but the assertions require deletion, locking in behavior that conflicts with the intended cleanup contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: rebase-push no-push fetch lacks transient retry
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `scripts/rebase-push.sh` hard-fails `git fetch` in `--no-push` mode without transient retry, unlike other fetch paths touched by this retry effort.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: create-pr conflict recovery list is unwrapped
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: After `gh pr create` reports an already-existing PR, conflict recovery uses an unwrapped `gh pr list`; a transient list failure prevents recovery despite an open PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] risk-integration: nested retry inside rebase-push lease loop multiplies pushes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: A transient retry inside the lease-race loop can multiply push attempts and add latency during sustained transient outages.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] code-quality: design-log temp files omitted from cleanup trap
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `list_fail_file` and `view_fail_file` are not included in the `wt_cleanup` trap, so early exits after `mktemp` can leak temp files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: security: design-log failure logs may emit unredacted retry output
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Push/create failure paths log raw retry output through `larch_err` without the redaction pipeline, so credentials or token-bearing URLs from git/gh output could reach breadcrumbs or committed logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: security: lib-net retry fail files need sensitivity handling
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `with_transient_retry` stores full stdout/stderr in a temp fail file until the caller removes it, creating exposure and logging risks if callers emit it without redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: correctness: retrying gh issue comment can duplicate public posts
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Wrapping `gh issue comment` in `with_transient_retry` is not idempotent; a server-side success followed by a transient client failure can post the same tracking, clarify, or audit comment multiple times.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.
