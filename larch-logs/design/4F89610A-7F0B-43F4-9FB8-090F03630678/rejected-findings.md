### [Plan Review] FINDING_1

### FINDING_1: OOS heading detection should ignore leading BOM/blank lines
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: `_is_oos_issue_body` can miss valid OOS templates when the body file begins with a BOM or blank line before `## Out-of-Scope Observation`, causing the issue to be filed without the required `[OOS]` prefix when `--title-prefix` is omitted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: `Specify strip of optional UTF-8 BOM and leading whitespace, then require the first non-empty line equals ## Out-of-Scope Observation; add a dry-run test with a leading newline before the heading`


### [Plan Review] FINDING_2

### FINDING_2: Regression coverage should exercise the live issue-create path
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The current regression coverage only verifies the dry-run branch, so a bug in the real `gh issue create` path could still leave OOS issues unprefixed while all tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: `Add one hermetic non-dry-run fixture that fakes gh issue create and asserts the emitted title or argv starts with [OOS] when the OOS body is used; keep the dry-run checks too.`


### [Plan Review] FINDING_3

### FINDING_3: OOS auto-prefixing should use a stricter body sentinel
- **Reviewer(s)**: Codex-dyn-Oos Prefix Correctness
- **Severity**: important
- **Concern**: Auto-prefixing based only on the first OOS heading is too broad and can misclassify ordinary or copied bodies as OOS, changing titles and downstream routing when the caller did not intend an OOS issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Oos Prefix Correctness: `Match the full fixed OOS wrapper shape, or another explicit sentinel, before injecting [OOS].`

