### FINDING_1: Report constant should be a concrete consumable symbol
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The report text and emitted constant currently point callers at the whole `TRACKING_ISSUE_PREFIX_BY_STATE` map instead of a concrete state-keyed prefix symbol, so the new lint would violate the issue-report contract and give unusable remediation text for match operands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Build the map from config.TRACKING_ISSUE_PREFIX_BY_STATE.items(), normalize each prefix for matching, and emit per-token constants such as TRACKING_ISSUE_PREFIX_BY_STATE["done"] (keep BUG_PREFIX for the bug token). Use the same state-keyed string in baseline constant fields and report lines.
  - From Cursor-Innovation: Build token-to-constant at runtime with the exact import path and state key (or BUG_PREFIX); emit that string in findings
  - From Cursor-Pragmatic: Build the runtime map to fully qualified replacements such as config.TRACKING_ISSUE_PREFIX_BY_STATE["done"] and title_match.BUG_PREFIX; emit those strings in findings and baseline constant field
  - From Cursor-Requirements: Build a normalized-token reverse map at lint init: lifecycle hits emit `TRACKING_ISSUE_PREFIX_BY_STATE["<state>"]` (or `config.TRACKING_ISSUE_PREFIX_BY_STATE["<state>"]`); bug hits emit `BUG_PREFIX`. Pin this in the report-format section and add a unit-test assertion on the emitted constant column.


### FINDING_6: Regex literals with escaped bracket tokens can be missed
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: major
- **Concern**: Matching only against the raw regex source text misses escaped bracketed lifecycle tokens, so real `re.compile(...)` sites using bracket escapes would ship unflagged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Normalize regex literals enough to match escaped bracket forms of tracked prefixes too, for example by also checking escaped variants derived from each tracked token before deciding no match
  - From Codex-Pragmatic: Normalize escaped regex text before substring matching, or search the de-escaped pattern so escaped bracketed tokens still match.


### FINDING_9: `not in` comparisons are omitted from the comparison scan
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-Ast Ratchet Reviewer
- **Severity**: major
- **Concern**: The comparison walker covers `in` but not `NotIn`, leaving a hole in the match-position contract for membership tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Handle `ast.NotIn` in the same compare-pair walker as `ast.In`, and add a `not in` test fixture.
  - From Cursor-dyn-Ast Ratchet Reviewer: Extend match-position coverage to `ast.NotIn` with the same literal/tuple/list/set operand rules as `in`


### FINDING_3: Baseline keying should include match context
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The baseline record does not pin the match-position context, so distinct hits on the same line can collapse into one identity and collide in occurrence, suppression, and write-shrink behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `context` to the typed baseline record and to `Finding.key()` (e.g. `startswith`, `compare_eq`, `regex_pattern`, `membership_in`), mirroring sibling ratchets that pin `access`/`callee`


