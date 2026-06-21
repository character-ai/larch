# Review Round 2

- Mode: `diff`
- 2 accepted, 5 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Embedded newlines fragment TSV rows before validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-generic-output.txt, dyn-tolerance-design-output.txt, dyn-migration-completeness-output.txt
- **Severity**: important
- **Concern**: The validator still iterates `text.splitlines()` before parsing, so embedded newlines inside `what`, `scenario_or_breakage`, or `suggested_fix` split one logical TSV row across physical lines. Fragments with fewer than eight tab columns are silently skipped; kept rows can stay at zero; `validate_structured_reviewer_output` returns exit 5; and the slot is dropped as `NOT_SUBSTANTIVE` despite valid-looking captured markdown. This matches the FD971172 / `cursor-plan-innovation` failure signature called out in the issue evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Join continuation lines until eight columns are present or emit _diag on every short-field skip; add a regression test with an embedded newline inside what/scenario_or_breakage
  - From cursor-specialist-edge-cases-output.txt: Pre-normalize or stitch continuation lines before per-row guards; add multiline-field regression test
  - From cursor-specialist-testing-output.txt: Implement multi-line row joining or pre-parse control-char normalization; add a regression test with a newline inside what/scenario before shipping as complete
  - From codex-generic-output.txt: Add row-continuation repair before validation, for example buffer lines after the TSV header until the next row-like prefix, fold embedded newlines in free-text fields to spaces, then split/clean the reconstructed row. Add a regression test for an embedded newline in each free-text field.
  - From dyn-tolerance-design-output.txt: add tests for tabs/newlines inside `what` and `scenario_or_breakage` showing reject-with-`_diag` or correct round-trip.
  - From dyn-migration-completeness-output.txt: Add multiline TSV row joining (continuation lines without a header prefix fold into the prior row before split), or reject with an operator-visible per-row reason; add regression tests for embedded newline and mid-row tab cases called out in the issue evidence.


### FINDING_2: Embedded tabs in early TSV columns mis-assign fields without rejection
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-tolerance-design-output.txt
- **Severity**: important
- **Concern**: `line.split("\t", 7)` only absorbs extra tabs into `suggested_fix` (column 8). A literal tab inside earlier columns (`location`, `what`, `scenario_or_breakage`) shifts field boundaries; with eight post-split segments the row can still pass enum guards while storing scrambled ballot content instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Validate column semantics after split, or normalize tabs inside fields before column assignment; add tests for mid-row embedded tabs
  - From cursor-specialist-edge-cases-output.txt: Reject over-wide tab splits or fold overflow consistently with tests for mid-row tabs
  - From dyn-tolerance-design-output.txt: Either normalize/reject before split (e.g. collapse or reject any data line whose raw tab count exceeds 7), parse with an 8-field-aware strategy that does not mis-assign earlier columns, or explicitly document and test that only `suggested_fix` overflow is tolerated; add tests for tabs/newlines inside `what` and `scenario_or_breakage` showing reject-with-`_diag` or correct round-trip.


