# Review Round 1

- Mode: `diff`
- 2 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Seven-field TSV salvage pads before re-split and mis-attributes free-text columns
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-dyn-salvage-robustness-output.txt
- **Severity**: important
- **Concern**: When a structured reviewer row splits to exactly seven tab-separated fields and the five leading typed columns validate, `_salvage_structured_tsv_row` pads an empty eighth column and returns before space-to-tab re-split. Rows where the missing delimiter sits between free-text columns (for example a two-or-more-space gap between `what`, `scenario_or_breakage`, and `suggested_fix`) are accepted into the ballot with shifted content: `scenario_or_breakage` and `suggested_fix` are wrong or blank, silently corrupting ballot content and downstream rendering (for example blank Proposed resolution). The seven-column pad path also assumes the only missing column is trailing `suggested_fix`; earlier omitted tabs produce the same silent column shift with no diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Try space-to-tab re-split before trailing pad when len(fields)==7; pad only as fallback
  - From cursor-specialist-edge-cases-output.txt: Gate trailing-pad salvage on evidence that only suggested_fix is missing, or reject ambiguous seven-field rows and surface the rows_seen diagnostic for retry
  - From codex-specialist-edge-cases-output.txt: Preserve trailing free-text in suggested_fix or treat ambiguous seven-field rows as repair/retry cases instead of always padding an empty field
  - From dyn-dyn-salvage-robustness-output.txt: For `len(fields) < 8`, try `re.sub(r" {2,}", "\t", line).split("\t", 7)` first when it yields eight fields with valid leading columns; only fall back to empty eighth-column padding when re-split does not produce a valid eight-column candidate. Add a regression test for the free-text double-space case above.
  - From dyn-dyn-salvage-robustness-output.txt: When padding to eight columns, treat ambiguous seven-field layouts as salvage failures unless re-split or another repair produces a high-confidence mapping (for example empty sixth column with non-empty seventh strongly suggests missing `scenario_or_breakage`); log a distinct reject reason instead of accepting shifted data.


### FINDING_3: Space-to-tab salvage may fabricate eight columns from multi-space prose inside a field
- **Reviewer(s)**: dyn-dyn-salvage-robustness-output.txt
- **Severity**: important
- **Concern**: When `len(fields) < 8` and the seven-column pad path does not apply, `re.sub(r" {2,}", "\t", line)` runs on the entire logical row without requiring delimiter-like gaps on column boundaries. A genuinely under-delimited row that contains intentional multi-space phrasing inside a free-text field can be fabricated into eight tab-separated fields, pass leading-column validation, and be accepted even though `scenario_or_breakage` and `suggested_fix` were never present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-salvage-robustness-output.txt: Restrict space-to-tab repair to delimiter-like gaps (for example only between the first five typed columns, or only when a run of spaces sits between tokens that match known enum/path patterns), or require post-salvage semantic checks before accepting; add a negative test that multi-space prose inside a single free-text field on an under-delimited row is still rejected.


