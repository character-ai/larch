### FINDING_1: Update per-kind test expectations
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Existing tests still pin legacy per-kind `needs_user_reason` and prose details, so they will fail once the ship flow emits combined `architectural-assessments` tokens with kind-only detail values even if behavior is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In ### UPDATED: python/tests/implement/test_ship.py, explicitly migrate those existing assertions to needs_user_reason=architectural-assessments and kind-only detail tokens; keep legacy-reason parametrization only where back-compat dispatch is under test


### FINDING_3: Align guidelines present-ref load rules
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The guidelines present-reference still reflects the legacy single-kind contract, so combined `assessments` pauses can be gated or described inconsistently through stale `When to load` and `Consumer` wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Replace the **When to load** prerequisite in `architectural-guidelines-present.md`: on `NEXT_ACTION=assessments` with `DETAIL` containing `guidelines`, load after guideline materialization exists regardless of invariant authoring status; retain the completed-invariant prerequisite only for back-compat `guidelines-assessment`
  - From Cursor-Requirements: Mirror the invariants present-ref plan: explicitly require updating **Consumer** and **When to load** to list primary `NEXT_ACTION=assessments` with `DETAIL` containing `guidelines`, plus back-compat `guidelines-assessment`, and the combined-path carve-out deferring relaunch to the parent branch.


### FINDING_6: Snapshot the resolved diff base
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The combined helper can still materialize invariant and guideline drafts from different resolved bases if the branch tip moves between prepare calls, which breaks the shared-evidence requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Freeze the resolved base SHA or the diff text once in the combined helper, and write both materialization files and metadata from that shared snapshot. Pin the test to matching diff fingerprints or base SHA, not only matching HEAD/base-ref arguments.


