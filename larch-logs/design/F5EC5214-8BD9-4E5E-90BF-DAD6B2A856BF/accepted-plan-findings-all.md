### FINDING_2: Preserve cross-kind materialization status fields
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Contract Parity
- **Severity**: major
- **Concern**: Invariant compose and gate paths use `ComposeMaterializationResult.guidelines_status` and `guidelines_path` as the knowledge-status carriers, while `_prepared_invariant_result` maps `guidelines_status` to `invariants_status`. Renaming, splitting, or generically reinterpreting these fields can break invariant gate classification and present-empty handling without a compile-time error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit preserved-contract row: keep ComposeMaterializationResult.guidelines_status as the shared materialization status field for both kinds (or add a compatibility property) and add a parity test that invariant prepare results still feed _prepared_invariant_result correctly
  - From Cursor-Pragmatic: Invariant compose paths overload ComposeMaterializationResult.guidelines_status as the knowledge-status carrier A generic compose helper that adds invariants_status/guidelines_status fields per kind, or renames the carrier, breaks invariant compose: _write_invariant_compose_materialization_metadata writes INVARIANTS_STATUS from materialized.guidelines_status and _prepared_invariant_result maps prepared.guidelines_status into InvariantsGateResult including present-empty Add an explicit Preserved contracts bullet for this internal wire; keep ComposeMaterializationResult field names unchanged; add a descriptor-policy regression that invariant prepare_compose still populates guidelines_status and still yields present-empty plus REASON_INVARIANTS_EMPTY through _prepared_invariant_result
  - From Cursor-dyn-Contract Parity: Invariant prepare and gate paths store knowledge status in ComposeMaterializationResult.guidelines_status and guidelines_path; ship_guidelines._prepared_invariant_result maps prepared.guidelines_status into InvariantsGateResult.invariants_status. Renaming those fields during generic unification breaks invariant gate and present-empty handling without compile errors. Add an explicit preserved-contract row: keep ComposeMaterializationResult field names guidelines_status and guidelines_path for both kinds. Add a descriptor-policy or parity test that invariant present-empty still surfaces REASON_INVARIANTS_EMPTY through prepared.guidelines_status.


### FINDING_6: Preserve distinct entry-body parsing policies
- **Reviewer(s)**: Cursor-dyn-Contract Parity
- **Severity**: major
- **Concern**: The descriptor field list does not capture the distinct body parsing policies: guideline parsing filters mechanized/detail bullets, while invariant parsing preserves verbatim bodies. A single regex-driven parser could change normalized knowledge snapshots and downstream assessment prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Contract Parity: Add parse_entries_callable or equivalent body-policy flag to AssessmentKind (mechanized-filter vs verbatim-body). Keep explicit parity tests on both parse_*_entries outputs, not only heading regex coverage.


### FINDING_8: Encode distinct design-time empty-content policies
- **Reviewer(s)**: Cursor-dyn-Contract Parity
- **Severity**: major
- **Concern**: Guidelines and invariants differ in how design-time empty content is persisted and how stale artifacts are removed. A generic empty-file policy could break design publish completeness and Gate C persistence flows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Contract Parity: Guidelines persist_design_assessment writes for present status even when content is empty; persist_invariant_design_assessment unlinks on absent/invalid or empty content, and invariants CLI sets requires_assessment only when content.strip() is non-empty. Generic empty-file policy would break design publish completeness and Gate C persist flows. Extend descriptor empty-file policy beyond ship present-empty: encode design-persist requires_nonempty_content and stale-artifact removal behavior per kind. Add explicit regression tests for present+empty guidelines vs invariants.


