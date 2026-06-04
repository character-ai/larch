### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: LOG_RECOVERY_BRANCH is redundant and may mislead future consumers
- **Reviewer(s)**: dyn-caller-exit-contract-output.txt
- **Severity**: latent
- **Concern**: `LOG_RECOVERY_BRANCH` is synthesized to equal `RECOVERY_BRANCH` and is not read by the live renderer path, creating ambiguity for future consumers that might expect a distinct meaning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-caller-exit-contract-output.txt: Either document in `design-publish.md` that `LOG_RECOVERY_BRANCH` is always identical to `RECOVERY_BRANCH` and exists for legacy compatibility, or drop the redundant key since no current consumer reads it and the exported env var `DESIGN_LOG_RECOVERY_BRANCH` already covers the one live use.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: reg_checks_rc is intentionally unused but only acknowledged by a no-op
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `reg_checks_rc` is captured but not semantically used; without an explanatory comment, future maintainers may incorrectly treat the `gh pr checks` exit code as the registration signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Replace `: "$reg_checks_rc"` with a `# shellcheck disable=SC2034` comment, or simply remove the captured rc assignment and the no-op.
  - From cursor-specialist-security-output.txt: Add a one-line comment immediately after the assignment: `# rc intentionally unused; JSON array content — not gh's exit code — is the registration signal (see #3413)`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

