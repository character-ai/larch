---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_1

### FINDING_1: Comma-separated suppression directives need one whole-directive identity
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: Comma-separated module-header suppressions need a whole-directive grammar and baseline identity. If the scanner splits one header into per-code rows or only matches single-code forms, it can miss live suppressions, mis-handle shared reasons, or churn the baseline on harmless comma-list edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add accepted file-header shapes `# ruff: noqa: CODE[, CODE...] # reason`, `# pyright: reportFlag=false[, reportFlag=false...] # reason`, and `# pylint: disable=check[, check...] # reason`. Pin baseline identity to one row per full normalized comment `text` (whole comma list), with one trailing `# reason` for the entire suppression. Document the same rule for bracket lists in `# type: ignore[...]` and `# pyright: ignore[...]`. Add pass/fail tests for comma-separated file headers and multi-code bracket ignores.
  - From Cursor-Innovation: Add an explicit rule and tests: one identity per matched tool directive (full comment-token text); comma-separated codes share one trailing `# reason` (pyright/pylint/type) or one `- reason` segment (noqa/ruff); add pass cases for comma pyright/ruff headers and a fail case if an implementer emits multiple rows from one header line.
  - From Cursor-Pragmatic: Add explicit rules that one comment token is one finding with `text` equal to the normalized full directive; cover fail/pass cases for comma-separated `# pyright: report…=false`, `# ruff: noqa: …`, and `# pylint: disable=…` headers; add a fixture based on a real header block and assert bootstrap emits one row per header comment.


### [Plan Review] FINDING_2

### FINDING_2: Following-line reasons need a negative test
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The same-line reason rule is not fully pinned by the required tests. Without a negative fixture for a reason on the next line, an implementation could accept following-line comments as valid reasons and still pass the listed coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a failing fixture where the suppression is on one line and the reason is on the immediately following comment line; assert the scanner still reports a violation.
  - From Cursor-Innovation: Add `Adjacent following-line reasons do not suppress a finding` to the required pytest cases, mirroring the existing preceding-line test.
  - From Cursor-Pragmatic: Add one negative test: suppression on line N with reason text only on line N+1 must still fail.


---LARCH-REJECTED-END---
