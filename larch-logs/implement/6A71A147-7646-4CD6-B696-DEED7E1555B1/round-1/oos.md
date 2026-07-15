### OOS_1: [OUT_OF_SCOPE] Runtime artifacts are not bound to run IDs
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Reusing a run directory may allow report-only execution to consume stale runtime artifacts.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: [OUT_OF_SCOPE] Mechanical verdicts precede triage
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: Mechanical verdicts can mask pre-existing triage, which is outside the current change scope.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: [OUT_OF_SCOPE] Planned runtime integration coverage is missing
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-runtime-evidence
- **Severity**: minor
- **Concern**: Planned integration coverage for runtime promotion, report rendering, and snapshot accounting is largely absent.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: [OUT_OF_SCOPE] Predicate-version changes discard predecessor snapshots
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The predicate-version bump can make the first post-upgrade report appear to have no compatible predecessor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Document the predicate bump in SKILL.md release notes; no code change required if intentional.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_5: [OUT_OF_SCOPE] SUSPECT verdicts lack a report count bucket
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Runtime `SUSPECT` rows affect totals without a dedicated report metric.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a SUSPECT count column in a follow-up reporting change.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_6: [OUT_OF_SCOPE] `runtime_main` does not use `--ledger-path`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The required ledger argument is unused, which may mislead callers about runtime-stage ledger validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Remove the unused arg or wire ledger consistency checks if that was the intent.
  - From cursor-specialist-testing: Remove or use the argument in a follow-up if desired.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
