### FINDING_1: Unavailable notes are treated as non-stale
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `_note_fingerprint_stale` treats `NOTE_STATE_UNAVAILABLE` as not stale, while tests cover consumable and non-stale behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_2: Coverage advancement is transactional
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `_advance_note_coverage` writes snapshot and metadata via temporary files and rolls back the snapshot when metadata replacement fails; `test_coverage_advancement_metadata_failure_restores_prior_artifacts` covers this behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_3: Authored invariant violations are preserved
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `write_unavailable_note` skips overwriting an authored invariant violation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_4: Advancement proves the stored HEAD snapshot
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Advancement re-materializes and fingerprints the stored `HEAD_SHA` diff before allowing the coverage increment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_5: Advancement preserves authored identity
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Advancement sets `AUTHORED_DIFF_FINGERPRINT` from the resolved identity before updating compatibility `DIFF_FINGERPRINT`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_6: Compose precheck invokes safe coverage advancement
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `_compose_precheck_result` calls `note_consumable` with `repo_root`, allowing safe HEAD advancement on the Step 8 reuse path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_7: Git failure modes are covered by tests
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `test_incremental_paths_out_of_scope_rejects_bad_git_output` covers nonzero exit, missing NUL terminators, and decode failures. Path classification, identity separation, validator extensions, and ship outcome classification match the plan. Ledger items marked `rejected` or `oos` were not re-raised without new evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
