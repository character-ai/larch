Non-actionable security pass observations from `cursor-specialist-security-output.txt` raw FINDING_4-FINDING_8 were omitted because they describe preserved mitigations, not behavioral risks requiring fixes.

### FINDING_1: Result-env allowlist omits publish recovery fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-publish-state-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-publish.md` documents an allowlist that omits `PR_NUMBER`, `PR_URL`, `RECOVERY_BRANCH`, and `LOG_RECOVERY_BRANCH`, even though `design-publish.sh` now emits them. This creates contract drift for operators, harness authors, and downstream parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-publish-state-output.txt: Address the concern above.

### FINDING_2: Head OID comparison is case-sensitive
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Registration compares `pr_head_oid` and `PUSH_HEAD_SHA` with case-sensitive equality. If GitHub and git return the same SHA with different ASCII casing, registration can time out and leave the flush PR open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: Registration-phase `gh pr view` failures lack test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The stub supports `GH_STUB_PR_VIEW_RC`, but no test exercises persistent `gh pr view` failures while checks JSON is non-empty. Regressions in registration failure handling could ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Automated publish increases operational exposure
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Re-enabling automated publish increases how often trimmed/redacted design artifacts land on the default branch via admin merge. The reviewer marked this as product intent and pre-existing operational risk, not a gate bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Admin merge still bypasses human review
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/design-log-publish.sh` still relies on admin merge privileges and GitHub branch-protection semantics. The reviewer marked this as unchanged and documented behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Plan-review collector stderr refactor is unrelated
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-publish-state-output.txt
- **Severity**: nit
- **Concern**: The plan-review collector stderr handling changed in the same branch, but reviewers marked it as unrelated to the publish/merge-gate work and primarily a robustness or diagnostic concern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-publish-state-output.txt: Address the concern above.

### FINDING_7: Failed publish recovery metadata is not surfaced reliably
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-publish-state-output.txt
- **Severity**: important
- **Concern**: After a failed flush, recovery metadata such as `PR_URL`, `RECOVERY_BRANCH`, and `LOG_RECOVERY_BRANCH` is emitted but not consistently replayed through failure logs, Step 5c parsing, or WARN lines. Operators may have to inspect tmpdir artifacts to recover the stuck flush PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-publish-state-output.txt: Address the concern above.

### FINDING_8: Completion watch can hang indefinitely
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Registration polling is bounded, but the subsequent `--watch` phase has no local timeout. A hung required check can block the design tail indefinitely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Non-array registration JSON is immediately fatal
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A non-array JSON response on the first registration probe is treated as fatal instead of potentially transient, which can skip the grace period and leave `PUBLISH_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Cumulative stub counters undermine stale-head race tests
- **Reviewer(s)**: dyn-gh-stub-output.txt
- **Severity**: important
- **Concern**: Test knobs such as `GH_STUB_CHECKS_JSON_EMPTY_FIRST` and `GH_STUB_PR_HEAD_OID_MISMATCH_FIRST` are keyed off cumulative sidecar counters. Multi-publish cases can silently stop exercising intended registration-race or stale-head behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-stub-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] Harness head-OID modeling can diverge from pushed worktree
- **Reviewer(s)**: dyn-gh-stub-output.txt
- **Severity**: latent
- **Concern**: The harness models `headRefOid` from `TEST_CLONE_ROOT` / `TEST_MERGE_BRANCH`, which can diverge from the publish worktree’s pushed commit if env leaks or branches are mismatched. One related allowlist-failure case was explicitly marked out of scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-stub-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] Integration stub does not cover registration polling races
- **Reviewer(s)**: dyn-gh-stub-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-multi-round-integration.sh` uses a slimmer `gh` stub. Reviewers marked full merge-gate race and stale-head behavior as covered elsewhere, so this is an out-of-scope integration coverage gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-stub-output.txt: Address the concern above.

### FINDING_13: Final summary implies publish success after failed flush
- **Reviewer(s)**: dyn-publish-state-output.txt
- **Severity**: important
- **Concern**: Post-publish summary rendering still uses an approved outcome and `PR N/A` even when `PUBLISH_OK=false` after a real flush created an open PR and recovery branch. The terminal summary can imply log publish completion when recovery is still needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-state-output.txt: Address the concern above.

### FINDING_14: Plan-review collector temp file leaks on early return
- **Reviewer(s)**: dyn-temp-cleanup-output.txt
- **Severity**: nit
- **Concern**: In `plan-review-loop.sh`, the new collector stderr temp file is removed only on the later path. An early `return 1` can leave `plan-review-collector.stderr.*` files in `$DESIGN_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-cleanup-output.txt: Address the concern above.

### FINDING_15: Registration temp files are not covered by cleanup trap
- **Reviewer(s)**: dyn-temp-cleanup-output.txt
- **Severity**: nit
- **Concern**: `design-log-publish.sh` creates registration-phase temp files that are removed on the happy path but are not included in `wt_cleanup`. Mktemp failure or interruption during registration can orphan temp files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-cleanup-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Push mktemp failure has inconsistent recovery semantics
- **Reviewer(s)**: dyn-temp-cleanup-output.txt
- **Severity**: nit
- **Concern**: `push_fail_file` mktemp failure still exits through `emit_publish_result false` / `exit 0` rather than the newer `emit_publish_failure` / `exit 1` path. Reviewer marked this as out of scope for the registration-loop temp cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-temp-cleanup-output.txt: Address the concern above.
