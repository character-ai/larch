### FINDING_1: Ambiguous structural assertion IDs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Assertion IDs 27 and 28 cover multiple unrelated greps, so CI failures do not identify which design-structure contract pin regressed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Duplicated repo validation helpers may drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `validate_repo` logic is duplicated across scripts with differing exit semantics, making future security or validation changes likely to drift between entry points.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: Clarify publish fail-closed contract is prompt/grep-only
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-summary-contracts-output.txt
- **Severity**: important
- **Concern**: Clarify publish normalization, failed-publish branching, and ordering before rename are enforced mainly by SKILL.md prose and structural greps, not runnable behavior, so the orchestrator can regress without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-summary-contracts-output.txt: Address the concern above.

### FINDING_4: Run-log synthesis and outcome documentation are incomplete
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-summary-contracts-output.txt
- **Severity**: latent
- **Concern**: The run-summary path has split guard authority and stale outcome documentation; direct `render-run-summary.sh` callers can still synthesize run-log paths for `publish-skipped`, while docs omit newer `publish-skipped` and `failed-publish` contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-summary-contracts-output.txt: Address the concern above.

### FINDING_5: Redundant pause-save repo validation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `design-pause-save.sh` validates the repo again after resolving it, adding redundant work and minor readability cost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Pause-save and pause-load repo validation mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Pause-save’s new repo validation is looser than pause-load’s `--*` rejection, leaving inconsistent pause-family validation for edge-case repo strings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Clarify failed-publish summary loses recovery metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-publish-flow-output.txt, dyn-summary-contracts-output.txt
- **Severity**: important
- **Concern**: Step 0b clarify parses `DESIGN_LOG_*` recovery metadata, but the final summary runs in a separate shell without exporting those variables, so failed-publish summaries can omit log flush PR and recovery branch bullets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-publish-flow-output.txt: Address the concern above.
  - From dyn-summary-contracts-output.txt: Address the concern above.

### FINDING_8: Publish-skipped footer and outcome contract are confusing
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The Step 5d footer can imply a design log was published when `SESSION_ID` is empty, and the final-summary outcome contract omits `publish-skipped`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Step 5c failed-publish sentinel behavior lacks behavioral coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Withholding `.completed/step-5c` on failed publish is only prompt/grep enforced, so an orchestrator regression could mark Step 5c complete after `PUBLISH_OK=false` and cause resume to skip publish retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: Malformed repo tests are too narrow
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The malformed `--repo` test only covers `/abs`, so weaker validation could still accept other invalid shapes such as `bad..repo` or `a/b/c`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Internal pause checkpoint lacks invalid source-env repo coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no regression test proving an invalid `REPO` from `source-env` fails before internal pause-save execution during Step 2b.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Final summary accepts unvalidated repo values
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `render-final-summary.sh` uses `--repo` to build issue URLs without validating the repo string, allowing malformed or misleading terminal summary links from compromised or incorrect upstream input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Auto-resolved design-publish repo is not revalidated
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-repo-binding-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` validates argv `--repo`, but auto-resolved `REPO` from `gh`/`resolve-repo.sh` is used downstream without a second validation pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-repo-binding-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Pause-save sources executable source-env before validation
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-repo-binding-output.txt
- **Severity**: latent
- **Concern**: `design-pause-save.sh` sources `$DESIGN_TMPDIR/source-env.sh` before validating extracted fields, so a same-UID writer can execute shell and still provide syntactically valid repo/session values afterward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From dyn-repo-binding-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Publish-skipped Step 5c completion can prevent resume retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-publish-flow-output.txt
- **Severity**: latent
- **Concern**: Step 5c is marked complete when `SESSION_ID` is empty because that is treated as “publish did not fail,” so a publish-skipped run may not self-heal on resume.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-publish-flow-output.txt: Address the concern above.

### FINDING_16: Non-zero publish envelope handling is under-specified
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-publish-flow-output.txt
- **Severity**: latent
- **Concern**: Non-zero `design-log-publish.sh` exits with publish-envelope stdout are not fully covered or normalized; recovery cases can fall into generic nonzero handling rather than recovery-oriented `PUBLISH_OK=false` handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-publish-flow-output.txt: Address the concern above.

### FINDING_17: Clarify rename gate references a nonexistent sub-step
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The rename gate references sub-step 3.3, which does not exist, risking mis-ordering of rename versus publish normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Clarify and Gate C use different no-log-flush terminal outcomes
- **Reviewer(s)**: dyn-publish-flow-output.txt
- **Severity**: nit
- **Concern**: Clarify exits with `cancelled-clarify` when publish is skipped, while Gate C uses `publish-skipped`; this may confuse operators even if intentional.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-flow-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Positive coverage/implementation observation
- **Reviewer(s)**: dyn-publish-flow-output.txt, dyn-summary-contracts-output.txt
- **Severity**: nit
- **Concern**: Reviewers observed that the main publish-flow implementation and harness coverage generally align with acceptance criteria for Gate C, fail-closed envelopes, skipped publish, and run-log suppression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-publish-flow-output.txt: Address the concern above.
  - From dyn-summary-contracts-output.txt: Address the concern above.

### FINDING_20: Step 0b fetches issue before resolving explicit repo
- **Reviewer(s)**: dyn-repo-binding-output.txt
- **Severity**: important
- **Concern**: Step 0b calls `gh issue view "$ISSUE_NUMBER"` before resolving and validating `REPO`, so it can read an issue from the hub default while later mutations target a different explicit repository.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-binding-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Plan block write omits explicit repo
- **Reviewer(s)**: dyn-repo-binding-output.txt
- **Severity**: latent
- **Concern**: `design-publish.sh` invokes `plan-block-write.sh` without `--repo`, so plan writes can target the hub default while publish/rename paths use an explicit repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-binding-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] write-design-current-env repo validation is weaker
- **Reviewer(s)**: dyn-repo-binding-output.txt
- **Severity**: nit
- **Concern**: `write-design-current-env.sh` uses regex-only repo validation that is slightly weaker than newer duplicated helpers, though the reviewer did not identify a functional bypass introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-repo-binding-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Primary and degraded fallback note ordering differs
- **Reviewer(s)**: dyn-summary-contracts-output.txt
- **Severity**: nit
- **Concern**: Recovery/skipped-publish note ordering still differs between primary and degraded fallback summaries; this predates the branch and is covered by separate assertions rather than byte parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-summary-contracts-output.txt: Address the concern above.
