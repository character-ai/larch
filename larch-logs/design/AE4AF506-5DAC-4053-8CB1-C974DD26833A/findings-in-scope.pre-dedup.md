### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan.txt:46-50,159-160
- **Concern**: Occurrence stability after suppression is untested. Scenario: A lint that renumbers after an earlier inline suppression will change later occurrence keys and churn the shrinking baseline.
- **Proposed resolution**: Add a two-hit fixture with the first match suppressed and assert the later finding still records occurrence 2.



### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: plan.txt:73-76,87-105
- **Concern**: Composite operand branches are untested. Scenario: python/larch/state/admission.py:49 already uses a tuple-valued `.startswith(...)`, and the plan also calls for tuple/list/set operands and chained comparisons, so a direct-string-only test suite can still pass.
- **Proposed resolution**: Add fixtures for one tuple-valued startswith/endswith case, one mixed container in/not in case, and one chained comparison.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_lifecycle_prefix_literal.py
- **Concern**: [SCOPE-REDUCTION] Drop `.removeprefix` and `.lstrip` from flagged match positions. Scenario: The binding issue scopes operands of `==`/`!=`/`in`, `.startswith`/`.endswith`, and `re.*` string patterns only; no production `python/larch` site uses `.lstrip("[DONE]")`-style lifecycle literals, and the only `removeprefix("[...]")` hit is display parsing in `design_terminal.py`
- **Proposed resolution**: Remove `.removeprefix`/`.lstrip` from the position list, visitor, sample report, edge cases, and mandatory tests; keep the lint aligned with the issue contract



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/lifecycle-prefix-literal-baseline.json
- **Concern**: Baseline identity omits match-position `context`. Scenario: The `Finding` dataclass names `context`, but the baseline record contract never pins it; two hits on one line with the same token and constant (e.g. `title.startswith("[DONE]")` and `title == "[DONE]"`) would share an identity and make occurrence/suppression/`--write` shrink logic collide
- **Proposed resolution**: Add `context` to the typed baseline record and to `Finding.key()` (e.g. `startswith`, `compare_eq`, `regex_pattern`, `membership_in`), mirroring sibling ratchets that pin `access`/`callee`



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_lifecycle_prefix_literal.py
- **Concern**: Constant hints ignore trailing-space semantics. Scenario: Canonical prefixes include trailing spaces (`"[DONE] "` in `config.TRACKING_ISSUE_PREFIX_BY_STATE`), but production literals such as `_report.py:363` use `.upper().startswith("[DONE]")` without that space; always emitting `config.TRACKING_ISSUE_PREFIX_BY_STATE["done"]` is not a drop-in fix and can change title classification
- **Proposed resolution**: When the matched literal normalizes to a token without the canonical trailing space, qualify the hint (e.g. `config.TRACKING_ISSUE_PREFIX_BY_STATE["done"].rstrip()`) or document that title checks must use casefold-based prefix logic rather than raw constant substitution



### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/issue/issue_wire.py:33
- **Concern**: Regex detection only covers exact or escaped bracket forms. It can miss tracked prefixes embedded as bare alternatives inside regex source.. Scenario: Current production regexes in `python/larch/issue/issue_wire.py`, `python/larch/issue/_util.py`, and `python/larch/issue/combine_issues.py` match lifecycle titles through alternations like `DONE` and `IMPLEMENTING`. If the lint only searches for bracketed literals, those sites ship unflagged.
- **Proposed resolution**: Broaden regex scanning to also recognize tracked tokens inside alternations and other debracketed regex text, or document and test that these regex forms are intentionally in scope.



