### FINDING_1: Harness grep pins at lines 105/113 still require retired marker-first literals
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements
- **Severity**: blocking
- **Concern**: The plan retitles callsite greps at ~124–127 but does not update harness assertions at ~105 and ~113 that still grep for `/design` marker-first and anti-halt `marker-first profile` literals in `skills/shared/final-summary-emit.md`. After the shared-doc row rename and SKILL anti-halt edits land, those pins still require retired strings, so `make test-harnesses-2` / `scripts/test-render-cost-line-callsites.sh` fails in CI even when runtime and prose are correct. An implementer can update only the four cited greps and leave 105/113 unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend `### UPDATED: scripts/test-render-cost-line-callsites.sh` to explicitly replace ~105 with a `/design` Read-always row pin and ~113 with a Read-always readiness-profile anti-halt pin (keep implement marker-first greps at ~106-107 unchanged).
  - From Cursor-Innovation: Extend the harness subsection to explicitly replace line 105 with a `/design` Read-always shared-row pin and line 113 with the new anti-halt Read-always readiness cite substring (or retire both with a comment) alongside the 124-127 updates
  - From Cursor-Pragmatic: Extend `### UPDATED: scripts/test-render-cost-line-callsites.sh` to explicitly replace lines 105 and 113 with Read-always readiness pins (e.g. shared row label and anti-halt pointer substring), not only the four callsite greps at 124-127
  - From Codex-Requirements: Update the `shared_final_summary` grep to match the new `/design` readiness-row text, and keep the harness pin on the renamed callsite row.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_2: Read-always profile omits authoritative `FINAL_SUMMARY_PATH` when stdout has multiple rows
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: `step5c_core` emits `FINAL_SUMMARY_PATH` in `_emit_core_kvs` before render; `result_env` can leave that value empty while `_emit_final_summary_marked_from_disk` later emits the real path plus empty readiness markers. An orchestrator that binds the first `FINAL_SUMMARY_PATH=` row may skip Read and show no summary despite a rendered disk file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the new Read-always section, require: after empty `LARCH_FINAL_SUMMARY_BEGIN/END` markers are present, bind the last non-empty `FINAL_SUMMARY_PATH` from completed notification stdout (or treat empty early rows as non-authoritative); mirror the rule at SKILL.md / `finalize-step5.md` callsites.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: Anti-halt prose still implies verbatim marker-body emit after markers become readiness-only
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan swaps the profile pointer to Read-always but does not retarget operative emit language. Anti-halt still says "shared verbatim final-summary emit" while markers become empty readiness signals. Orchestrators can treat empty marker pairs as a completed verbatim emit and never Read `FINAL_SUMMARY_PATH`, reproducing empty chat after Python stops streaming bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: At ~line 29 (and the Step 5d "verbatim full-body emit" sibling at ~720), replace marker-body emit language with: parse `FINAL_SUMMARY_PATH` from completed stdout, confirm empty readiness markers, then Read and emit the disk file verbatim.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Wrapper contract doc still claims marker bodies stream between `LARCH_FINAL_SUMMARY_BEGIN/END`.
- **Description**: Wrapper contract doc still claims marker bodies stream between `LARCH_FINAL_SUMMARY_BEGIN/END`.. Scenario: `skills/design/SKILL.md` cites `design-step5c.md` as the Step 5c contract; invariant line 22 still describes body emission into the contract stream after the helper change.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step5c.md:22
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_2: Companion harness doc still describes `/design` marker-first row enforcement.
- **Description**: Companion harness doc still describes `/design` marker-first row enforcement.. Scenario: The `.sh` harness is updated in-plan, but the paired `.md` still tells maintainers to pin marker-first design bindings, inviting reintroduction of retired greps.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/test-render-cost-line-callsites.md:9-18
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Wrapper contract still says final-summary body is emitted between LARCH_FINAL_SUMMARY markers though SKILL.md cites design-step5c.md as the Step 5c contract
- **Description**: [OUT_OF_SCOPE] Wrapper contract still says final-summary body is emitted between LARCH_FINAL_SUMMARY markers though SKILL.md cites design-step5c.md as the Step 5c contract. Scenario: Maintainers or agents loading the wrapper doc after the helper change will believe marker bodies still traverse task stdout and may debug the wrong surface
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-step5c.md:22
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

### OOS_4: Wrapper contract still documents full marker-body emission between LARCH_FINAL_SUMMARY_BEGIN/END
- **Description**: Wrapper contract still documents full marker-body emission between LARCH_FINAL_SUMMARY_BEGIN/END. Scenario: Maintainers loading design-step5c.md on Step 5c paths may reintroduce marker-body extraction after Python emits empty readiness markers only
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: skills/design/scripts/design-step5c.md:22
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected

