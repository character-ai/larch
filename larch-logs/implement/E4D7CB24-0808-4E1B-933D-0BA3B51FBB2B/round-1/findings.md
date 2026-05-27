### FINDING_1: [OUT_OF_SCOPE] Branch 1 bootstrap table lists stale rename/init order
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Branch 1 resume documentation in `skills/implement/SKILL.md` still lists `larch-log.sh init` before the best-effort implementing rename, while runtime now performs the rename first. This documentation drift could mislead maintainers or runbook updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: B4-family tests do not assert rename-before-post ordering
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: B4-family tests assert that the implementing rename happened, but they do not prove it happened before `post-tracking-issue.sh` or `larch-log` initialization. A future reorder could move the rename after metadata posting while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] Sentinel/adopt prose omits early rename ordering
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Sentinel idempotency prose does not mention early rename ordering for Branch 2 adopt, so operators reading only that bullet may misunderstand when the title changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: POSTED=false defer can leave issue blocked as [IMPLEMENTING] without sentinel
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: If the early rename succeeds but `post-tracking-issue.sh` returns `POSTED=false`, `parent-issue.md` is removed while the GitHub issue title remains `[IMPLEMENTING]`. A fresh `/implement` can then hit managed-prefix admission exit 5 unless the operator manually reverts the title, preserves the tmpdir/sentinel, or a follow-up adds rollback/admission carve-out behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: tracking-init-failed documentation still implies a late rename can occur
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The `tracking-init-failed` row still describes a stalled rename as if it can apply after the early-rename relocation, but the implementing rename now already ran before init failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_6: Feature expectation for title reset on blocked work is not implemented
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The feature asks for title reset when work cannot proceed, but the plan/code do not roll the title back to `[DESIGNED]` on `tracking-init-failed` or `POSTED=false` paths. This was described as an accepted trade-off, but should be reopened if automatic reset remains a product requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Successful Branch 2/adopt paths lack rename presence/order coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: GP-adopt and GP2 tests do not assert that the implementing rename happens. A regression could remove the rename from successful Branch 2 adopt or Branch 1 resume while defer-path tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: B5 stall paths lack rename-attempt assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: B5 and B5-branch1 stall tests do not assert that the implementing rename was attempted before tracking init failure. A partial revert could leave issues `[DESIGNED]` while the stall path still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Unrelated #3056 branch changes may confuse review/CI attribution
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The full branch diff includes unrelated #3056 ship/merge/lint-fix-loop/version/log changes. Broader CI failures may be misattributed to the #2975 rename work unless reviewers isolate the feature commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] B4 harness documentation omits rename-on-defer behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `test-implement-bootstrap.md` omits the new B4 behavior where `POSTED=false` still performs the rename before defer and sentinel removal, which could lead contributors to assume the old contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Title-prefix admission relies on collaborator-mutable metadata
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Managed-prefix admission gates depend on GitHub issue titles, which collaborators can mutate independently of actual workflow state. This is pre-existing design rather than a new issue from the rename relocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Resume branch can bypass current title admission state
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: A preserved `IMPLEMENT_TMPDIR` with matching `parent-issue.md` can resume despite the GitHub title changing since adoption, because the resume branch skips managed-prefix and missing-`[DESIGNED]` checks. This is documented pre-existing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Plan-fidelity output includes commit inventory rather than a behavioral finding
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The plan-fidelity reviewer surfaced commit inventory and traceability notes for `774a7237`, `d39dd867`, and `3b602a6f`; these do not identify a distinct fixable behavioral risk beyond the merged findings above.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
