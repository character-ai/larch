### FINDING_1: Result-env allowlist omits publish recovery fields
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-publish-state-output.txt
- **Severity**: important
- **Concern**: `skills/design/scripts/design-publish.md` documents an allowlist that omits `PR_NUMBER`, `PR_URL`, `RECOVERY_BRANCH`, and `LOG_RECOVERY_BRANCH`, even though `design-publish.sh` now emits them. This creates contract drift for operators, harness authors, and downstream parsers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-publish-state-output.txt: Address the concern above.


### FINDING_10: Cumulative stub counters undermine stale-head race tests
- **Reviewer(s)**: dyn-gh-stub-output.txt
- **Severity**: important
- **Concern**: Test knobs such as `GH_STUB_CHECKS_JSON_EMPTY_FIRST` and `GH_STUB_PR_HEAD_OID_MISMATCH_FIRST` are keyed off cumulative sidecar counters. Multi-publish cases can silently stop exercising intended registration-race or stale-head behavior.
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


### FINDING_3: Registration-phase `gh pr view` failures lack test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The stub supports `GH_STUB_PR_VIEW_RC`, but no test exercises persistent `gh pr view` failures while checks JSON is non-empty. Regressions in registration failure handling could ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Failed publish recovery metadata is not surfaced reliably
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-publish-state-output.txt
- **Severity**: important
- **Concern**: After a failed flush, recovery metadata such as `PR_URL`, `RECOVERY_BRANCH`, and `LOG_RECOVERY_BRANCH` is emitted but not consistently replayed through failure logs, Step 5c parsing, or WARN lines. Operators may have to inspect tmpdir artifacts to recover the stuck flush PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-publish-state-output.txt: Address the concern above.


