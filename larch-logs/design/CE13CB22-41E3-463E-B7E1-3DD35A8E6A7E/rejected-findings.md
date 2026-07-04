### [Plan Review] FINDING_1

### FINDING_1: Missing `site=` rows still count as escalation evidence
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The row-evidence helper treats missing or empty `site=` values as if they were ordinary non-step3-review evidence, so malformed or legacy ledger rows can still make `escalation_evidence_present()` true and allow an `escalation-success` report on an otherwise approved run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require parseable site= and trigger= before a row can qualify; then count rows only when site is present and not step3-review, or when site=step3-review and trigger is in STEP3_ESCALATION_FAILURE_STATUSES. Add a missing-site ledger/fallback negative test alongside the planned malformed/no-trigger case.


### [Plan Review] FINDING_2

### FINDING_2: Step 3 contract docs still point normal handoffs at escalation recording
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The Step 3 reference contract in `skills/design/references/plan-review.md` still describes `record-escalation` as owned by normal handoff statuses, even though those paths are now meant to be routing-only no-op evidence paths. That leaves the shipped contract stale and still aligned with the bug class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add this file to the firm updates and change the sentence to say only genuine Step 3 failures record escalation evidence; normal handoffs are routing-only and prompt-side orchestration still must not call `record-escalation` manually.

