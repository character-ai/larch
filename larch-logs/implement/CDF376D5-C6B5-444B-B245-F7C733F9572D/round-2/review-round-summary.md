# Review Round 2

- Mode: `diff`
- 3 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Partial new-format metadata can falsely claim authored coverage
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: New-format metadata falls back from a missing authored fingerprint to `DIFF_FINGERPRINT`, contrary to the required fail-closed identity rules. A partial or corrupted modern sidecar can therefore be consumed as proven assessment coverage despite missing authored or covered identity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Apply DIFF_FINGERPRINT fallback only to records with no new-format fields; require both identities for all new-format authored and deterministic-clean records and add a partial-metadata regression test.
  - From codex-specialist-edge-cases: Allow DIFF_FINGERPRINT fallback only when all new-format fields are absent; otherwise require explicit authored and covered fingerprints.


### FINDING_2: Compose-precheck safe-advance reuse lacks integration coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Compose-precheck integration tests do not prove that safe HEAD advancement returns `status=current` or that `load_or_prepare_*` reuses coverage after docs-only or log-only commits. A regression in `_compose_precheck_result` or invariant-only advancement could force unnecessary reassessment despite working `note_consumable` advancement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add tests that advance HEAD safely, then call prepare_compose_assessment and prepare_invariant_compose_assessment with matching expected_head_sha and assert status=current.
  - From cursor-specialist-testing: Add repo-backed tests for prepare_compose_assessment and prepare_invariant_compose_assessment returning current after safe drift, plus load_or_prepare_* needs_assessment=False.
  - From codex-specialist-testing: Add guideline and invariant prepare-compose tests asserting status=current and refreshed covered metadata after safe HEAD advances.


### FINDING_6: Coverage rollback is not verified after metadata replacement failure
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Coverage refresh rollback does not verify that restoration succeeded after metadata replacement fails. A later I/O failure can leave a new snapshot paired with old metadata even though advancement returns false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Use a recoverable transaction or generation marker, verify rollback, and fail loudly when durable consistency cannot be restored.
