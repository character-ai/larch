# Review Round 1

- Mode: `diff`
- 12 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Validate the frozen snapshot against the recorded coverage identity
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Materialization validation trusts the mutable frozen-diff fingerprint without independently verifying that the snapshot matches the recorded covered commit and base. A corrupted snapshot could be replaced with a docs-only diff and matching metadata, causing deterministic-clean output while omitting code changes. Independently derive the recorded base-to-HEAD diff and compare it with the frozen snapshot before filtering, launching, or persisting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_2: Isolate persistence failures by kind
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: A combined-launch persistence failure causes unavailable artifacts to be written for every pending kind, including kinds that already persisted successfully. A later kind's HEAD-drift or deviation-log failure can overwrite a valid first-kind assessment. Track durable state per kind and persist unavailable artifacts only for unresolved kinds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_3: Preserve invariant violations during unavailable fallback
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: `_persist_unavailable()` rewrites the outcome even when unavailable-note persistence preserves an existing invariant violation. A later launcher, schema, or persistence failure can therefore pair a preserved violation note with an unavailable/clean outcome and suppress the invariant at the ship gate. Preserve the matching invariant violation outcome and receipt whenever the valid violation remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_4: Validate and consume unavailable receipts on re-entry
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-agent-boundary
- **Severity**: major
- **Concern**: Re-entry accepts unavailable notes based on note/outcome consumption or HEAD matching without validating the coordinator-owned unavailable receipt. Stale, missing, incomplete, or tampered receipts can suppress reassessment, while valid unavailable state may be relaunched unnecessarily. Validate receipt schema, kind, covered identities, materialization identity, durable note/outcome hashes, and file safety before treating the state as handled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-agent-boundary: Address the concern above.


### FINDING_5: Route post-launch HEAD drift through incremental coverage recovery
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Post-launch HEAD drift is converted into unavailable results for all pending kinds instead of using Piece 1 incremental coverage handling. Docs-only, logs-only, or otherwise irrelevant commits can discard valid authored work, while relevant changes do not refresh only the affected kind. On HEAD mismatch, re-enter coverage advancement and materialization logic before deciding whether relaunch or unavailable fallback is required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_6: Make deviation-log persistence retryable without relaunch
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness
- **Severity**: major
- **Concern**: A failed `append_deviation_note` is handled as unavailable or is omitted from handled detection. Re-entry can relaunch Claude or lose the authored deviation instead of retrying only the missing log append. Validate deviation-log persistence in `_already_handled`, retain an authored-and-log-pending state, and retry the append without relaunching when the note and outcome are valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.


### FINDING_7: Treat empty diffs as ambiguous
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Whitespace-only or path-less frozen diffs are treated as deterministic-clean through vacuous filtering. Empty parsed path sets should be treated as ambiguous and routed to authored assessment rather than skipping Claude.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_8: Return a usage error for invalid or empty kinds
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Invoking the CLI without `--kind` reports an internal failure instead of a usage error. Validate kinds in `main()` and return `EXIT_USAGE` for invalid argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_9: Add the plan-required coordinator integration tests
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The plan-required offline integration matrix is missing. Materialization, local-git identity checks, fake-launcher behavior, re-entry idempotence, unavailable receipts, HEAD drift, partial combined persistence, invariant preservation, and CLI stdout/exit contracts remain insufficiently verified. Add the plan-listed integration and regression tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_10: Validate Git metadata before subprocess use
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-agent-boundary
- **Severity**: minor
- **Concern**: `HEAD_SHA` and `BASE_REF` from materialization metadata reach `git rev-parse` without the allowlist validation used elsewhere. Reject malformed, whitespace-containing, or option-like values with the existing commit/base-ref validators before any Git invocation, failing closed on invalid metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-agent-boundary: Address the concern above.


### FINDING_11: Confine the production launcher to the evidence directory
- **Reviewer(s)**: dyn-dyn-agent-boundary
- **Severity**: major
- **Concern**: The launcher uses the repository root as `cwd` while granting the evidence directory through `--add-dir`. This can make live repository files or secrets readable outside the validated frozen evidence boundary. Launch with `cwd` confined to the evidence directory or another empty directory, keep `--add-dir` limited to that directory, and pass only evidence-local absolute paths in `REQUESTS_JSON`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-agent-boundary: Address the concern above.


### FINDING_12: Re-verify copied evidence artifacts immediately before launch
- **Reviewer(s)**: dyn-dyn-agent-boundary
- **Severity**: major
- **Concern**: Copied evidence artifacts are not re-verified as regular, non-symlink files within the evidence directory immediately before subprocess launch. A same-UID symlink swap could redirect agent reads outside the intended snapshot. Re-check the evidence directory and every launch artifact with regular-file and containment validation at use time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-agent-boundary: Address the concern above.
