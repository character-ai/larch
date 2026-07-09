### FINDING_1: Single relaunch only after all assessment writers finish
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Step8 Routing Integrator
- **Severity**: major
- **Concern**: The present-reference and SKILL path still force an immediate Step 8 relaunch after each compose write, which would split the combined assessments route into two relaunch rounds and can let the first writer finish before the second note is authored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a combined-path carve-out in both present refs (and a one-line supremacy note in the SKILL assessments branch): under NEXT_ACTION=assessments defer all relaunch to the orchestrator until every DETAIL-requested writer succeeds; keep per-ref relaunch text only for back-compat invariants-assessment and guidelines-assessment
  - From Cursor-Innovation: Add an explicit combined-path carve-out to both present references and the SKILL assessments branch: when DETAIL lists more than one kind defer Step 8 relaunch until all requested compose wrappers succeed and ignore per-reference relaunch lines until then
  - From Cursor-Pragmatic: In the `### UPDATED:` sections for both present refs, add an explicit combined-path carve-out: on `NEXT_ACTION=assessments`, follow SKILL ordering, do not relaunch after the first writer, and relaunch Step 8 only once after every DETAIL kind succeeds. Optionally add the same supersede line to the `assessments` bullet in skills/implement/SKILL.md.
  - From Cursor-Requirements: Add a combined-path carve-out in both present refs (defer relaunch to the parent `assessments` branch until all DETAIL-listed writers succeed) and/or an explicit override in the SKILL `assessments` branch: ignore per-ref relaunch lines until every requested kind is written.
  - From Cursor-dyn-Step8 Routing Integrator: Add an explicit combined-path carve-out in both present refs (defer relaunch until all `DETAIL` kinds are written; back-compat branches keep per-kind relaunch), update `When to load` for same-turn invariant-first ordering, and change the harness pins at lines 55/64 to assert the carve-out instead of unconditional per-ref relaunch.


### FINDING_2: Canonical combined-assessment token contract is missing
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Step8 Routing Integrator, Codex-dyn-Step8 Routing Integrator
- **Severity**: major
- **Concern**: The combined assessments route needs one authoritative contract for `NEEDS_USER_REASON`, `DETAIL`, and resume tokens, or the code, SKILL text, and exit matrix will disagree about which action token to emit, where to read it from, and how to parse it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update required-artifacts bullets for the combined path: NEEDS_USER_REASON=architectural-assessments and DETAIL contains invariants and/or guidelines; retain old reason lines only under an explicit back-compat sub-bullet
  - From Cursor-Pragmatic: In ship.py, build `assessment_kinds` explicitly and set `ShipResult.detail` to `",".join(assessment_kinds)` only. Reserve gate `detail` strings for back-compat per-kind reasons and violation paths.
  - From Cursor-Requirements: Document in exit matrix and SKILL: read `DETAIL` from `.ship-route-exit-handoff.env`; allowed tokens are exactly `invariants` and/or `guidelines` comma-separated without spaces; reject empty, unknown, or duplicated tokens.
  - From Codex-Requirements: Parse `DETAIL` into the allowed tokens `invariants` and `guidelines`, require at least one recognized kind, and fail closed as Tool Failure on any missing, duplicate, or unknown token before running writers or relaunching Step 8.
  - From Cursor-dyn-Step8 Routing Integrator: Specify in SKILL and exit-matrix: read `DETAIL` then `DETAIL_FILE` from `.ship-route-exit-handoff.env`; accept only `invariants`, `guidelines`, or `invariants,guidelines` (trim tokens); Tool Failure on empty/unknown tokens; run writers strictly in that order; relaunch once only after all listed writers succeed.
  - From Codex-dyn-Step8 Routing Integrator: Update both prompts to describe `NEXT_ACTION=assessments` as the primary resume token, keep `guidelines-assessment` only as legacy back-compat, and document `DETAIL` as the kind list for the combined route.


### FINDING_3: Combined gate path must snapshot the compose base once and avoid early return
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Step8 Routing Integrator
- **Severity**: major
- **Concern**: The combined gate path must snapshot the compose base once and evaluate both gates before any early return; otherwise HEAD drift or an invariants-first exit can still produce mismatched diffs or two pauses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Resolve the base ref to a stable commit once in the helper, or thread a frozen base SHA through both compose-assessment preparers before either gate runs.
  - From Cursor-Innovation: In the combined helper capture compose_head_sha and compose_base_ref once then pass them into both gate evaluations (add optional snapshot args or inline the shared materialization path) before returning architectural-assessments
  - From Cursor-Requirements: In the ship.py section, state explicitly: run both gates (violation short-circuit excepted), build `assessment_kinds`, and remove the pre-guidelines `needs_assessment` return on the combined pre-PR and post-rebase refresh paths.
  - From Cursor-dyn-Step8 Routing Integrator: Implement `_compose_assessment_gate_before_pr` (or equivalent) that snapshots HEAD/base once, runs invariant then guideline gates without early return, builds `assessment_kinds` from each `needs_assessment`, materializes both inputs when listed, returns one `ShipResult(..., needs_user_reason="architectural-assessments", detail=...)`, and keep the invariant-violation return ahead of the combined assessment return.


### FINDING_6: [OUT_OF_SCOPE] Fence-shape harness still only asserts the old ordering
- **Reviewer(s)**: Cursor-dyn-Step8 Routing Integrator
- **Severity**: minor
- **Concern**: The fence-shape harness still only checks the legacy branch ordering, so it can miss regressions in the new assessments branch placement and one-relaunch sequencing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Step8 Routing Integrator: [OUT_OF_SCOPE] Promote `scripts/test-implement-fence-shape.sh` to UPDATED and add an `assessments`-slice assertion: invariant compose write before guideline compose write before exactly one Step 8 bgjob relaunch.


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


