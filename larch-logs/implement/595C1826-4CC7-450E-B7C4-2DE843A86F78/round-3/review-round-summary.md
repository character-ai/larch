# Review Round 3

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: `_split_structured_tsv_row` rejects >8 tab fields instead of merging overflow into `suggested_fix`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `_split_structured_tsv_row` rejects any row with more than eight tab-separated fields instead of folding overflow into the free-text tail (`suggested_fix`). A Cursor finding with an embedded tab in `what`, `scenario_or_breakage`, or `suggested_fix` still yields exit 5 and the slot is dropped as `NOT_SUBSTANTIVE`, leaving the third reported failure mode (FD971172 innovation class) unfixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Split on first seven tabs and join remainder into suggested_fix with _clean_tsv; add regression test for 9+ column rows
  - From codex-generic-output.txt: Fold overflow fields back into the free-text tail instead of rejecting the row, and change the regression test that currently expects embedded-tab rejection.


### FINDING_2: `_location_field_valid` rejects valid non-file plan locations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: The new location validator rejects structured findings whose `location` is a plan section or other non-file anchor, even though the reviewer contract allows non-file locations when a repo-relative file line is not applicable. Bare `plan.txt` without `:line` (observed in larch-logs design B0F7B604) fails `FILE_LINE_REGEXES`, and a valid plan-review row such as `location=Testing strategy` now returns exit 5, potentially zeroing the slot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Remove or relax location regex for structured-reviewer TSV; accept any non-empty cleaned location
  - From codex-generic-output.txt: Remove the hard file-location requirement, or allow documented non-file anchors such as plan sections while keeping tab-shift detection separate.


### FINDING_3: `_iter_tsv_logical_rows` finalizes rows too early, truncating `suggested_fix` continuations
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_iter_tsv_logical_rows` yields at `>=8` tabs before joining continuation lines into `suggested_fix`. A physical newline inside `suggested_fix` truncates the fix and discards the continuation line as orphan prose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Defer row finalization until next row start or EOF when continuations lack a leading digit-tab prefix


