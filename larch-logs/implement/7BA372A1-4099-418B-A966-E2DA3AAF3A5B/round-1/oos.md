### FINDING_5: [OUT_OF_SCOPE] Stale conflict-recovery documentation and reference assertions
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-step8-route
- **Severity**: minor
- **Concern**: `conflict-resolution.md` and related Step 8 recovery documentation still describe compose-time or guidelines-only reassessment after `HEAD`/diff movement. This conflicts with the adapter-first combined normalization route and can lead operators to bypass normalization or use stale assessments after conflict recovery. The related harness assertions were also removed or are not being updated in this plan surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-step8-route: Sweep `skills/implement/references/conflict-resolution.md` (and any sibling Step 8 recovery docs) to describe ship-driver reassessment through the combined adapter route and scoped pre-filter reuse; restore negative assertions in `test-architectural-guidelines-step.sh` so stale `guidelines-assessment`-only recovery prose fails CI.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_6: [OUT_OF_SCOPE] Harness contract documentation is stale
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-step8-route
- **Severity**: minor
- **Concern**: `test-architectural-guidelines-step.md` still says that the live prompt owns assessment authoring and Step 8 relaunching, and references the older warning-appender contract. Maintainers may rely on this stale contract when modifying tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-step8-route: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Closure baseline drift
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: `python/skill-closure-baseline.json` changed outside the eight-file plan surface, altering conditional files for implement. Unrelated closure drift could mask or confuse future skill-loading audits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Adapter integration harness is not wired into default CI
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `test-step-8-assessment.sh` is not wired into the Makefile or CI shards, so adapter regressions in identity, retry, and fail-closed paths may merge without default-branch coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Security trust-boundary prose lacks mechanical coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The Step 8 trust-boundary statements in `SECURITY.md` have no mechanical harness coverage, allowing SECURITY.md and SKILL.md to diverge on delegation validation or inline-fallback prohibitions without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Normalization whitespace contract is inconsistent
- **Reviewer(s)**: dyn-dyn-step8-route
- **Severity**: minor
- **Concern**: The normalization prose rejects whitespace-repaired tokens as Tool Failure, while the adapter trims surrounding whitespace on kind tokens. This weakens the stated fail-closed normalization contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-step8-route: Address the concern above.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false
