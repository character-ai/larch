### FINDING_3: [OUT_OF_SCOPE] Step 8 invariant compose coverage is incomplete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-arch-knowledge
- **Severity**: major
- **Concern**: `python/tests/implement/test_ship.py` and `python/tests/core/test_architectural_guidelines.py` still leave the Step 8 invariant mirror under-tested, so empty-file stalls, resume ordering, and the broader plan-required integration and harness assertions can regress.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-arch-knowledge: Add the planned integration tests and harness assertions in the same change: empty invariants do not block compose, `architectural-invariants-violation` maps to `ci-fix`, `phase=invariants-assessment` resume, invariant-before-guideline PR/final-summary ordering, and the invariant compose wrapper fixture.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_4: [OUT_OF_SCOPE] invariant-first approval gating is not enforced
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: `skills/design/references/approval-gates.md` and `skills/design/references/design-outline.md` still lack an invariant-first branch, so active invariant violations can reach approval or skip-approve without remediation or persisted evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] the invariant flush helper is unwired
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-arch-knowledge
- **Severity**: minor
- **Concern**: The invariant flush helper exists but is never called from the PR path, so invariant sidecars still depend on guideline flush staging and the mirror is fragile if that ordering changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-arch-knowledge: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: symlink-following temp writes can clobber files
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The invariant artifact temp-write path follows symlinks, which can let a symlinked `$IMPLEMENT_TMPDIR` artifact path corrupt another same-user file before replace.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_14: [OUT_OF_SCOPE] run-log-batches docs omit invariant schema details
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-arch-knowledge
- **Severity**: minor
- **Concern**: The run-log batch docs do not document `invariants_status`, invariant reason tokens, or the invariant outcome cutover, so consumer drift can go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-arch-knowledge: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_15: [OUT_OF_SCOPE] PR-body consumer tests do not cover invariant sections
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The PR-body and related consumer tests were not extended for the invariant sections, so rendering and batch validation can regress outside the main ship path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_17: [OUT_OF_SCOPE] conflict-recovery prose is stale
- **Reviewer(s)**: dyn-dyn-arch-knowledge
- **Severity**: minor
- **Concern**: The post-rebase recovery prose still asks for `NEXT_ACTION=guidelines-assessment` instead of the invariant-first `invariants-assessment` relaunch, so the recovery path is out of date.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-arch-knowledge: Address the concern above.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

