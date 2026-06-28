### OOS_1: [OUT_OF_SCOPE] Whitespace-only severity cells enter baseline voter-severity lists
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: After DictReader migration, a TSV severity cell containing only spaces is truthy and becomes `(none)` in severities, shifting modal baseline buckets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use .strip() before truthiness checks on severity columns.

### OOS_2: [OUT_OF_SCOPE] Targeted-fetch degradation duplicates `analyze_issues` helper inline
- **Reviewer(s)**: dyn-dyn-realized-outcomes
- **Severity**: latent
- **Concern**: Targeted-fetch degradation is inferred inline via `__fetch_failed__` rather than calling `_ground_truth_targeted_fetch_degraded()` from `analyze_issues`, unlike `run_main()`. Behavior is likely equivalent today but duplicates logic and may drift if the helper's semantics change.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] `_false_negative_rows_from_tsv` malformed-row counter discarded
- **Reviewer(s)**: dyn-dyn-realized-outcomes
- **Severity**: nit
- **Concern**: `_false_negative_rows_from_tsv` counts `exonerated` / `out_of_scope` verdicts in a local `malformed_rows` counter that is discarded in `_parse_file_into_stats` (`_fn_malformed` ignored). That does not inflate reported corpus stats but makes the helper's accounting misleading for future reuse.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Pre/post false-negative subtables omit unknown-version skipped note
- **Reviewer(s)**: dyn-dyn-realized-outcomes
- **Severity**: nit
- **Concern**: Pre/post false-negative subtables implicitly exclude `period == "unknown"` (same as `_section_prepost`) but do not emit the `unknown-version skipped: N` note that baseline pre/post prints under `--since-version`. Diagnostic parity gap only; not introduced on the realized-outcomes surface.
- **Suggested revisions (informational for voters; coder decides)**:

