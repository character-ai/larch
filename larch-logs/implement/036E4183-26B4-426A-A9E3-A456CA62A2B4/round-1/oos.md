### FINDING_6: [OUT_OF_SCOPE] Acceptance checks miss isolated per-slot auto wording
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-cursor-routing
- **Severity**: minor
- **Concern**: Existing acceptance and docs-sync checks do not detect isolated phrases such as “per-slot `auto`,” allowing stale Cursor model guidance to survive future documentation sweeps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-cursor-routing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_7: [OUT_OF_SCOPE] CI recovery documentation order disagrees with configuration
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: `docs/external-reviewers.md:108` documents the CI recovery order as Claude → Codex → Cursor, while the configuration registry orders it as Codex → Cursor → Claude. Operators may therefore misunderstand the fixer waterfall sequence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Retry replay accepts legacy Cursor auto metadata
- **Reviewer(s)**: dyn-dyn-cursor-routing
- **Severity**: minor
- **Concern**: Retry replay still accepts any non-empty `OUTER_LAUNCHER_CURSOR_MODEL`, including legacy `auto` values from older `.meta` files, and forwards them as `--cursor-model`. New dispatches no longer write `auto`, so this affects only retries of pre-change artifacts in the same session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-cursor-routing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Missing static Cursor resolved-model assertion
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `python/tests/agents/test_external_dispatch.py:349-377` does not assert the static Cursor `resolved_model`. Existing dispatch integration coverage reduces the incremental risk, but the narrow unit-test assertion is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
