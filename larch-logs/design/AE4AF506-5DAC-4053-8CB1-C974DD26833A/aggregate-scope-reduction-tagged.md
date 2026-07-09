### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_lifecycle_prefix_literal.py
- **Concern**: [SCOPE-REDUCTION] Drop `.removeprefix` and `.lstrip` from flagged match positions. Scenario: The binding issue scopes operands of `==`/`!=`/`in`, `.startswith`/`.endswith`, and `re.*` string patterns only; no production `python/larch` site uses `.lstrip("[DONE]")`-style lifecycle literals, and the only `removeprefix("[...]")` hit is display parsing in `design_terminal.py`
- **Proposed resolution**: Remove `.removeprefix`/`.lstrip` from the position list, visitor, sample report, edge cases, and mandatory tests; keep the lint aligned with the issue contract
