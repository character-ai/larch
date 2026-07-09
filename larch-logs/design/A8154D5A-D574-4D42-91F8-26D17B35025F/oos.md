### FINDING_3: Baseline identity must exclude reason
- **Reviewer(s)**: Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Baseline matching cannot require the row reason as part of identity. If `reason` participates in the key, live findings may not match baseline rows, or the same suppression could be duplicated under different reasons, breaking shrink-only baseline behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Keep reason as a required record field, but exclude it from the matching, duplicate, stale-row, and write-preserve identity. Use file, suppression_kind, normalized text, and occurrence as the key.
  - From Codex-Requirements: Define the baseline identity as `file`, `suppression_kind`, `text`, and `occurrence`; keep `reason` as required validated metadata, not part of the matching key.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Plan scope bullets exclude `tests/` but the referenced iterator does not
- **Description**: Plan scope bullets exclude `tests/` but the referenced iterator does not. Scenario: The bullets require excluding `tests/`, while the implementation note copies `lint_subprocess_via_runner.iter_source_files`, whose `EXCLUDED_DIRS` omit `tests/`. Today every file under `python/tests/` is already skipped by the `test_*.py` filename rule, so behavior matches intent, but the mixed guidance invites an unnecessary `tests/` exclusion fork.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_subpression_reason.py
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

