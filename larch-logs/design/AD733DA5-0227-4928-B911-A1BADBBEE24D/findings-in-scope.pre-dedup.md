### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/tests/implement/test_ship.py:6611,6962,7168
- **Concern**: Existing tests still pin per-kind needs_user_reason and prose detail strings. Scenario: After ship.py emits architectural-assessments with kind-only detail (e.g. detail=guidelines), test_merge_rebase_stale_guidelines_note_triggers_reassessment, test_open_pr_resume_guidelines_gate_needs_assessment_skips_flush_and_ensure_pr, and the post-rebase stale-guidelines case will fail even when behavior is correct
- **Proposed resolution**: In ### UPDATED: python/tests/implement/test_ship.py, explicitly migrate those existing assertions to needs_user_reason=architectural-assessments and kind-only detail tokens; keep legacy-reason parametrization only where back-compat dispatch is under test



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:assessments branch
- **Concern**: [SCOPE-REDUCTION] Parent MANDATORY READ line says read both present-reference files when a kind is listed. Scenario: The sub-bullets load refs only when DETAIL contains invariants or guidelines, but the parent line can be read as always loading both refs on any single-kind pause, reintroducing rejected dual-read scope creep
- **Proposed resolution**: Reword the assessments branch to: read each present-reference file whose kind appears in DETAIL (load architectural-invariants-present.md only for invariants; load architectural-guidelines-present.md only for guidelines); keep the harness pin that both refs are read only when both kinds are listed



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/references/architectural-invariants-present.md:28-30 and skills/implement/references/architectural-guidelines-present.md:30-42
- **Concern**: Present-reference failure paths still mandate immediate Step 8 relaunch on combined `assessments` loads. Scenario: The plan adds combined-path carve-outs that defer success relaunch to the parent `assessments` branch, but both present refs still tell the orchestrator to relaunch Step 8 on compose-wrapper failure (and guidelines deviation-append failure). Under `NEXT_ACTION=assessments`, a failed invariant or guideline writer would follow per-reference relaunch prose and rerun Step 8 early, violating the plan edge case that forbids relaunch after a partial writer failure and recreating split-round behavior
- **Proposed resolution**: Add combined-path failure carve-outs to both present refs: on `NEXT_ACTION=assessments`, wrapper or deviation-append failure is Tool Failure; do not relaunch Step 8 from the per-reference contract. Extend `test-architectural-guidelines-step.sh` pins so combined-path refs explicitly defer failure relaunch to the parent branch while back-compat branches keep per-kind relaunch text



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/architectural-guidelines-present.md:7
- **Concern**: The guidelines present-reference load gate still blocks combined dual-kind authoring. Scenario: The plan adds `assessments` consumer bullets but only says to include them in **When to load**; it does not replace the existing prerequisite that guidelines load only after invariant assessment has completed cleanly. For `DETAIL=invariants,guidelines`, SKILL requires loading both present refs before invariant authoring, so the stale prerequisite contradicts the combined contract and can block or mis-order dual-kind pauses
- **Proposed resolution**: Replace the **When to load** prerequisite in `architectural-guidelines-present.md`: on `NEXT_ACTION=assessments` with `DETAIL` containing `guidelines`, load after guideline materialization exists regardless of invariant authoring status; retain the completed-invariant prerequisite only for back-compat `guidelines-assessment`



### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: The planned `assessments` branch defines success-path ordering and single relaunch but not fail-closed terminal routing when a listed compose write or guideline append-deviation helper fails.. Scenario: On `DETAIL=invariants,guidelines`, an invariant compose write failure or a guideline append-deviation-note / compose-write failure leaves combined-path supremacy blocking per-reference relaunch without telling the orchestrator whether to halt as tool-failure, stall, or continue; a partial turn can stop mid-sequence or follow stale present-ref relaunch prose.
- **Proposed resolution**: Add explicit `assessments`-branch failure bullets mirroring plan Failure modes: on any listed writer or append-deviation-note non-success, skip remaining DETAIL writers, do not relaunch Step 8 in the same turn, and route to the existing post-driver `tool-failure` (or documented stall) path; note that present-reference failure relaunch lines apply only to back-compat per-kind branches.



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/references/architectural-guidelines-present.md
- **Concern**: The guidelines present-reference update list is thinner than the invariants section and omits explicit **Consumer** / **When to load** header edits even though those headers currently name only `guidelines-assessment`.. Scenario: Implementers can update required-artifact bullets but leave Consumer/When-to-load naming only the legacy action, so combined-path operators loading the ref under `NEXT_ACTION=assessments` + `DETAIL` containing `guidelines` get contradictory load rules versus the invariants ref and exit matrix.
- **Proposed resolution**: Mirror the invariants present-ref plan: explicitly require updating **Consumer** and **When to load** to list primary `NEXT_ACTION=assessments` with `DETAIL` containing `guidelines`, plus back-compat `guidelines-assessment`, and the combined-path carve-out deferring relaunch to the parent branch.



### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py:430-493
- **Concern**: Combined pending-assessment path still flushes terminal guideline outcomes before writers run. Scenario: In an invariants-only combined pause, the helper must run the guideline gate to discover no guideline draft is needed. The existing guideline gate writes and flushes an outcome sidecar for absent, invalid, or current guidelines. That flush can commit larch-logs after the invariant diff is materialized, so step-architectural-invariants-write-compose.sh sees HEAD changed and refuses the draft. A repeated relaunch can hit the same self-inflicted HEAD change instead of delivering the single combined round.
- **Proposed resolution**: When any assessment kind is pending, defer run-log-flushing terminal outcome handling for non-pending gates until the next Step 8 pass after requested drafts are durable. Add focused coverage for the invariants-only plus terminal-guidelines case.



### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/core/architectural_guidelines.py:384-408
- **Concern**: Prior fix incomplete: the plan snapshots the base label, not the resolved diff base. Scenario: materialize_implementation_diff resolves origin/main and merge-base inside each prepare call. If origin/main advances between invariant and guideline materialization, both calls can receive the same compose_base_ref string while writing different merge-base..HEAD diffs. That violates the required same final diff and can produce two notes over different evidence.
- **Proposed resolution**: Freeze the resolved base SHA or the diff text once in the combined helper, and write both materialization files and metadata from that shared snapshot. Pin the test to matching diff fingerprints or base SHA, not only matching HEAD/base-ref arguments.



