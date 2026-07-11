# Review Round 2

- Mode: `diff`
- 7 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Post-launch HEAD drift bypasses incremental coverage recovery
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-agent-boundary
- **Severity**: major
- **Concern**: Any HEAD change after launcher execution currently routes directly to unavailable persistence. This discards valid authored assessments for irrelevant changes and fails to re-enter Piece 1 per-kind coverage advancement or rematerialize/relaunch only affected kinds for relevant changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-agent-boundary: Address the concern above.


### FINDING_2: Guideline deviation persistence is destructive and not validated as handled
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-agent-boundary
- **Severity**: major
- **Concern**: A successful authored guideline deviation can be overwritten by unavailable persistence when deviation-log append, outcome writing, postcondition validation, or a HEAD check fails. Re-entry also treats a deviation note/outcome as handled without validating the required execution-issues log entry. Preserve the authored note and outcome in a retryable log-pending state, validate log completion before reporting handled, and retry only the missing deduplicated append.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-agent-boundary: Address the concern above.


### FINDING_3: Combined launcher results are persisted all-or-nothing
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: A valid per-kind launcher result is discarded when another requested kind is missing or invalid. Persist independently valid rows and write unavailable artifacts only for unresolved or invalid kinds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_4: Current notes with invalid outcome sidecars are not repaired
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: A consumable note with an invalid outcome can make materialization fail for status=current, producing an internal failure instead of repairing the outcome sidecar or treating the kind as handled after validating postconditions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_5: Deterministic-clean persistence lacks an immediate HEAD recheck
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness
- **Severity**: major
- **Concern**: HEAD can move between materialization and deterministic-clean persistence, allowing a clean assessment to be written for stale evidence. Recheck HEAD immediately before persistence and fail closed or re-enter incremental coverage handling on mismatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.


### FINDING_7: Required coordinator integration coverage is missing
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The plan-required offline integration matrix is absent. Materialization identity, unavailable receipt re-entry, HEAD-drift recovery, partial persistence, invariant/deviation preservation, local-Git validation, fake-launcher behavior, and relevant CLI contracts lack regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_9: CLI usage and success stdout contracts lack regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `main()` usage-error and successful machine-readable stdout contracts are untested, leaving Piece 3 bgjob integration vulnerable to unnoticed exit-code or envelope regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
