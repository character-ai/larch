# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: dispatch can skip the architectural acknowledgment gate when schema metadata is missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: In `python/larch/implement/dispatch_step2.py`, the architectural acknowledgment check is effectively reached only after schema-version handling. That means a `complete` or `needs_qa` manifest with missing or non-`1` `schema_version` can fall into manifest-invalid recovery and emit `claude_fallback` instead of the non-recoverable `architectural-acknowledgment-missing` outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Run _require_architectural_acknowledgment before any _emit_manifest_invalid_or_recover branch when the snapshot requires knowledge and status is complete or needs_qa; add a missing-schema_version regression test asserting no RECOVERY_FROM=.
  - From codex-specialist-edge-cases: Move the acknowledgment check before missing-schema recovery for complete and needs_qa statuses


### FINDING_2: implementer self-validation does not enforce required architectural acknowledgment
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The implementer-side jq self-validation does not check `architectural_acknowledgment` when architectural knowledge blocks are present, so the plan-required guard is only enforced later in dispatch after a manifest has already been produced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_8: missing snapshot fallback tests for architectural acknowledgment enforcement
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: There is no coverage for absent or malformed `step2-architectural-knowledge.env`, so dispatch could regress into using live repo reads or skip acknowledgment enforcement when the snapshot is missing or invalid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add tests with present knowledge files and no snapshot or malformed snapshot values; assert fallback requires acknowledgment and well-formed false snapshot overrides present files
  - From codex-specialist-testing: Add absent-snapshot and malformed-snapshot dispatch tests that assert architectural-acknowledgment-missing and no RECOVERY_FROM


### FINDING_9: missing invalid-file prompt assembly coverage for architectural knowledge
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: There is no regression test for mixed validity in the architectural knowledge inputs during prompt assembly, so invalid files could leak into prompts, leave dangling instructions, or fail to emit the expected warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a test with invalid invariants and present guidelines; assert only the valid untrusted block is injected and invalid-path text is absent
  - From codex-specialist-testing: Add an invalid-reader-result prompt test that asserts omission, false snapshot when no valid file exists, and warning append


