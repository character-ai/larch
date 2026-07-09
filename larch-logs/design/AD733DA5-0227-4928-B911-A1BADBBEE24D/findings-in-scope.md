### FINDING_1: Update per-kind test expectations
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Concern**: Existing tests still pin legacy per-kind `needs_user_reason` and prose details, so they will fail once the ship flow emits combined `architectural-assessments` tokens with kind-only detail values even if behavior is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In ### UPDATED: python/tests/implement/test_ship.py, explicitly migrate those existing assertions to needs_user_reason=architectural-assessments and kind-only detail tokens; keep legacy-reason parametrization only where back-compat dispatch is under test

### FINDING_2: Add combined-path carve-outs to present refs
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The present-reference failure prose still forces immediate Step 8 relaunch on writer failures, which conflicts with the combined `assessments` flow and can reintroduce split-round behavior after a partial failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add combined-path failure carve-outs to both present refs: on `NEXT_ACTION=assessments`, wrapper or deviation-append failure is Tool Failure; do not relaunch Step 8 from the per-reference contract. Extend `test-architectural-guidelines-step.sh` pins so combined-path refs explicitly defer failure relaunch to the parent branch while back-compat branches keep per-kind relaunch text

### FINDING_3: Align guidelines present-ref load rules
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The guidelines present-reference still reflects the legacy single-kind contract, so combined `assessments` pauses can be gated or described inconsistently through stale `When to load` and `Consumer` wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Replace the **When to load** prerequisite in `architectural-guidelines-present.md`: on `NEXT_ACTION=assessments` with `DETAIL` containing `guidelines`, load after guideline materialization exists regardless of invariant authoring status; retain the completed-invariant prerequisite only for back-compat `guidelines-assessment`
  - From Cursor-Requirements: Mirror the invariants present-ref plan: explicitly require updating **Consumer** and **When to load** to list primary `NEXT_ACTION=assessments` with `DETAIL` containing `guidelines`, plus back-compat `guidelines-assessment`, and the combined-path carve-out deferring relaunch to the parent branch.

### FINDING_4: Define combined-assessment failure routing
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: The new combined `assessments` branch does not yet spell out fail-closed behavior for helper failures, so a writer or append-deviation failure can leave the turn in an undefined state or fall through to stale relaunch prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add explicit `assessments`-branch failure bullets mirroring plan Failure modes: on any listed writer or append-deviation-note non-success, skip remaining DETAIL writers, do not relaunch Step 8 in the same turn, and route to the existing post-driver `tool-failure` (or documented stall) path; note that present-reference failure relaunch lines apply only to back-compat per-kind branches.

### FINDING_5: Defer terminal guideline flushes
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The runtime still flushes non-pending terminal guideline outcomes too early in the combined assessment path, which can dirty `HEAD` before draft writers finish and cause self-inflicted relaunch failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: When any assessment kind is pending, defer run-log-flushing terminal outcome handling for non-pending gates until the next Step 8 pass after requested drafts are durable. Add focused coverage for the invariants-only plus terminal-guidelines case.

### FINDING_6: Snapshot the resolved diff base
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The combined helper can still materialize invariant and guideline drafts from different resolved bases if the branch tip moves between prepare calls, which breaks the shared-evidence requirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Freeze the resolved base SHA or the diff text once in the combined helper, and write both materialization files and metadata from that shared snapshot. Pin the test to matching diff fingerprints or base SHA, not only matching HEAD/base-ref arguments.

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:assessments branch
- **Concern**: [SCOPE-REDUCTION] Parent MANDATORY READ line says read both present-reference files when a kind is listed. Scenario: The sub-bullets load refs only when DETAIL contains invariants or guidelines, but the parent line can be read as always loading both refs on any single-kind pause, reintroducing rejected dual-read scope creep
- **Proposed resolution**: Reword the assessments branch to: read each present-reference file whose kind appears in DETAIL (load architectural-invariants-present.md only for invariants; load architectural-guidelines-present.md only for guidelines); keep the harness pin that both refs are read only when both kinds are listed
