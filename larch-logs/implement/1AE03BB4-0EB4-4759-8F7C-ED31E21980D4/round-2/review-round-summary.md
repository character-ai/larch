# Review Round 2

- Mode: `diff`
- 5 accepted, 5 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Snapshot artifacts are not revalidated before downstream use
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-artifact-context
- **Severity**: major
- **Concern**: The validated pre-coder snapshot identity is captured but never revalidated before cleanup, diff-base selection, path collection, staging, or commit. A same-UID process can replace snapshot artifacts after initial validation, causing downstream consumers to act on tampered evidence rather than fail closed. Later snapshot OSError or identity-mismatch paths can also escape the bounded `CoderResult` failure envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-artifact-context: `Thread the ValidatedPreCoderSnapshot returned from preparation through the coder lifecycle, and call revalidate_pre_coder_snapshot(snapshot) immediately before _cleanup_failed_coder_attempt, _collect_round_stage_paths, _write_attempt_pre_tracked_paths, and any patch-restore helper; fail closed into the existing bounded CoderResult/OSError envelope on mismatch.`


### FINDING_2: `disposition_link_kind` does not fail closed when coverage is absent
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: When `load_live_coverage` is `None` but a `proceed-partial` disposition artifact exists, `disposition_link_kind` returns `part-of` instead of failing closed. PR/finalize link rendering can then disagree with deferred-inventory and report consumers, and teardown may skip the expected `DONE` rename.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_3: Explicit manifest paths can silently fall back to a different manifest
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: When an explicit `manifest_path` is supplied but disappears, resolution falls back to a default manifest. A non-default manifest can therefore be replaced by a different artifact set during validation or rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_4: Plan-required trusted-artifact regression tests are missing
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-artifact-context
- **Severity**: major
- **Concern**: The branch lacks the planned regression coverage for invalid declared contexts, manifest-only contexts, invalid-present disposition and coverage artifacts, non-default manifest propagation, disposition-only helpers, PR-body rendering, finalize, final reports, and snapshot tampering or fail-closed paths. These security and consistency contracts can regress without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-artifact-context: `Add the planned tests for symlinked/partial/malformed disposition files, declared missing/symlinked tmpdirs, manifest-only context without a valid tmpdir, and consistent non-default manifest use across disposition_link_kind, disposition_deferred_inventory, and require_pr_mutation_scope_disposition.`


### FINDING_5: Post-validation snapshot failures can escape as uncaught errors
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: OSError paths occurring after initial snapshot preparation, including during stage-path collection or failed-attempt cleanup, are not consistently mapped to `CODER_STATUS=failed`. A snapshot that becomes partial or tampered mid-coder can crash Step 5 instead of producing the bounded failure result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
