# Review Round 1

- Mode: `diff`
- 9 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: PR creation ignores the explicit manifest path
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-artifact-context
- **Severity**: major
- **Concern**: The PR-create path calls `disposition_link_kind` without the authoritative `ctx.manifest_path`, even though mutation validation and existing-PR updates pass it through. With a non-default manifest, validation can use one disposition while PR-body link rendering discovers another, producing an incorrect `closes` versus `part-of` link.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-artifact-context: Address the concern above.


### FINDING_2: Final report hides a present-but-invalid disposition
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-artifact-context
- **Severity**: major
- **Concern**: `_plan_coverage_summary_line` returns an empty string when coverage is absent without checking whether a disposition artifact is present. A present-but-untrusted disposition can therefore be rendered as “no coverage” instead of failing closed with `ShipError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-artifact-context: Address the concern above.


### FINDING_3: Snapshot validation errors escape the bounded coder failure envelope
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: An `OSError` from present-invalid pre-coder snapshot validation can propagate during Step 5 or `mav-apply`, causing the runner to crash instead of returning the established failed `CoderResult`/`CODER_STATUS=failed` envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_4: Snapshot validation accepts unexpected root entries
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The validator checks required artifacts but does not enumerate the complete snapshot root. A snapshot containing the required files plus an unexpected file, directory, symlink, FIFO, or other non-regular entry can pass validation despite the fail-closed contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_5: Validated snapshot identity is not rechecked before downstream use
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-artifact-context
- **Severity**: major
- **Concern**: `artifact_identity` is captured during initial validation but discarded or not revalidated before cleanup, diff-base selection, attempt capture, path collection, staging, and coder launch. A same-UID process can replace or rewrite snapshot artifacts after validation, allowing tampered content to drive cleanup or staging decisions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-artifact-context: Address the concern above.


### FINDING_6: Planned regression coverage is missing for trusted-artifact consumers
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: The branch lacks the plan-required regression coverage for scope disposition, PR-body/create behavior, finalize, final report, review-and-fix, invalid-present artifacts, declared context, invalid tmpdirs, and non-default manifest propagation. These omissions leave the newly changed fail-closed and manifest-identity paths vulnerable to regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_7: SECURITY.md does not document the trusted-artifact enforcement
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: The plan-required `SECURITY.md` enforcement bullets are absent, so the new trusted-artifact fail-closed behavior is not documented as part of the security contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_8: Missing direct tests for invalid-present disposition handling
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The `load_disposition` fail-closed behavior lacks direct branch coverage for malformed or symlinked present artifacts and for `disposition_deferred_inventory`, leaving possible fallback to `closes` or an empty inventory untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_9: Missing focused test for manifest propagation through PR-body composition
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No test asserts that `_compose_pr_body_for_pr_create` passes the same explicit manifest path to disposition helpers that the mutation gate validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
