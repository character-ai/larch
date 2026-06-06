### FINDING_1: `--bail-reason` report-only split breaks existing argv-only classification coverage
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Cursor-Pragmatic, Codex-Edge, Cursor-Requirements, Codex-Requirements, Cursor-dyn-skill-site-coverage, Codex-dyn-skill-site-coverage
- **Severity**: important
- **Concern**: The planned `classify_bail`/`report_bail` split removes argv-only `--bail-reason` from `classify_from_evidence`, but the existing case 7b harness expects `--bail-reason "network timeout while posting issue"` to classify as `transient-infra`. Unless the plan preserves that behavior or explicitly updates the contract/tests, the harness will fail and the plan’s “keep existing classify cases green” / “no classifier behavior change” claims are false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update Testing strategy: revise or remove case 7b (e.g. move network-timeout evidence into ship-pr-state.sh BAIL_REASON or a failure-detail log) and document that --bail-reason is report-only, not classification evidence
  - From Codex-Arch: Keep the split narrow: let allowlisted Step-2 dispatch tokens from bail_arg participate in failure_class classification while still excluding the argv overlay from the signature hash if that is the stability goal, or persist the sanitized Step-2 reason into an existing durable classifier input before Step 18a. Update the existing bail-reason-only harness case accordingly.
  - From Cursor-Edge, Cursor-Pragmatic: Revise the Testing strategy / test-stall-recovery-report.sh section to rewrite or drop case 7b and, if transient-infra-from-bail coverage is still wanted, assert it via state/session BAIL_REASON or validated failure-detail evidence instead of argv-only bail
  - From Codex-Edge: Revise the split so existing --bail-reason classification behavior is preserved, or explicitly update the contract/tests and narrow the Step-18a handoff to a separate report-only path for FINAL_BAIL_REASON rather than changing --bail-reason globally
  - From Cursor-Requirements: Add an explicit test-plan step to rewrite or drop case7b (e.g. move the transient-infra trigger into session/state evidence for classification and add a separate argv-only report-bail assertion)
  - From Codex-Requirements: Revise the plan to preserve --bail-reason as classification evidence while excluding the argv overlay only from BAIL_REASON reporting/signature where needed, or explicitly update the existing test/docs and state this intentional routing change.
  - From Cursor-dyn-skill-site-coverage: Add to test-stall-recovery-report.sh section: revise or remove case 7b (e.g. assert unrecoverable or move network markers into state/evidence) and note the intentional argv-routing regression in the harness doc
  - From Codex-dyn-skill-site-coverage: Update case7b to the new report-only contract, or narrow the split if bail-reason-only routing must remain supported.

### FINDING_2: Step-2 in-memory bail reasons can lose routing evidence
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: Some Step-2 hard-bail paths may only carry dispatcher reasons such as `wrapper-validation-failure` in memory and pass them to Step 18a via `--bail-reason`. If the split excludes that argv value from classification before the reason is persisted into state/session evidence, `classify_from_evidence` can emit `unrecoverable` instead of `dispatch-failure`, skipping first-detection issue filing or retry behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Keep the split narrow: let allowlisted Step-2 dispatch tokens from bail_arg participate in failure_class classification while still excluding the argv overlay from the signature hash if that is the stability goal, or persist the sanitized Step-2 reason into an existing durable classifier input before Step 18a. Update the existing bail-reason-only harness case accordingly.
  - From Codex-Innovation: Keep bail_arg in the classification input for the existing allowlisted dispatch bail tokens, or seed/read the Step-2 bail as state/session evidence before excluding argv from classify_from_evidence

### FINDING_3: Step 2.4 recovery bail reason mirror is missing
- **Reviewer(s)**: Codex-dyn-skill-site-coverage
- **Severity**: latent
- **Concern**: The plan’s concrete SKILL.md mirror touch sites cover §2.1.5 and §2.2, but Step 2.4 also assigns `FINAL_BAIL_REASON=recovery-out-of-scope`. If that path is not mirrored to `IMPLEMENT_BAIL_REASON`, Step 18a may render the bail reason as `none` instead of the expected redacted fail-closed reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-skill-site-coverage: Add the recovery-out-of-scope assignment to the SKILL.md mirror pass, or explicitly state that this path is excluded because it does not route through the Step 12d stall handoff.
