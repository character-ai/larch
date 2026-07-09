### [Plan Review] FINDING_1

### FINDING_1: Occurrence keys after suppression need coverage
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: Occurrence numbering can shift after an inline suppression, which would churn later occurrence keys and destabilize the shrinking baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a two-hit fixture with the first match suppressed and assert the later finding still records occurrence 2.


### [Plan Review] FINDING_2

### FINDING_2: Composite operand branches lack direct fixtures
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Concern**: The test surface does not exercise tuple-valued starts/ends, mixed membership containers, or chained comparisons, so a string-only suite could pass while missing these branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add fixtures for one tuple-valued startswith/endswith case, one mixed container in/not in case, and one chained comparison.


### [Plan Review] FINDING_4

### FINDING_4: Trailing-space semantics need explicit handling in hints
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: Canonical lifecycle prefixes include trailing spaces, but some production literals do not; always substituting the canonical constant can change classification unless the hint accounts for that normalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: When the matched literal normalizes to a token without the canonical trailing space, qualify the hint (e.g. `config.TRACKING_ISSUE_PREFIX_BY_STATE["done"].rstrip()`) or document that title checks must use casefold-based prefix logic rather than raw constant substitution


### [Plan Review] FINDING_5

### FINDING_5: Regex scanning must catch debracketed alternations too
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Regex detection that only recognizes exact or escaped bracket forms can miss lifecycle tokens embedded as bare alternations, leaving real production regexes unflagged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Broaden regex scanning to also recognize tracked tokens inside alternations and other debracketed regex text, or document and test that these regex forms are intentionally in scope.


### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_lifecycle_prefix_literal.py
- **Concern**: [SCOPE-REDUCTION] Drop `.removeprefix` and `.lstrip` from flagged match positions. Scenario: The binding issue scopes operands of `==`/`!=`/`in`, `.startswith`/`.endswith`, and `re.*` string patterns only; no production `python/larch` site uses `.lstrip("[DONE]")`-style lifecycle literals, and the only `removeprefix("[...]")` hit is display parsing in `design_terminal.py`
- **Proposed resolution**: Remove `.removeprefix`/`.lstrip` from the position list, visitor, sample report, edge cases, and mandatory tests; keep the lint aligned with the issue contract


