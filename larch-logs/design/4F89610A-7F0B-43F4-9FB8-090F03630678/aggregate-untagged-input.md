### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/issue_create.py
- **Concern**: _is_oos_issue_body must ignore leading BOM/blank lines before matching the OOS template heading. Scenario: /issue Step 6 writes oos-body-<i>.txt by hand assembly; a leading newline before ## Out-of-Scope Observation makes naive startswith fail, so create-one still files without [OOS] when --title-prefix is omitted
- **Proposed resolution**: Specify strip of optional UTF-8 BOM and leading whitespace, then require the first non-empty line equals ## Out-of-Scope Observation; add a dry-run test with a leading newline before the heading

### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/issue/test_issue_create.py:306-336
- **Concern**: The proposed regression tests only exercise the dry-run branch.. Scenario: A bug could still leave the real gh issue create path unprefixed while every new test passes, so the fix would be unverifiable on the live execution path.
- **Proposed resolution**: Add one hermetic non-dry-run fixture that fakes gh issue create and asserts the emitted title or argv starts with [OOS] when the OOS body is used; keep the dry-run checks too.

### FINDING_3:
- **Reviewer(s)**: Codex-dyn-Oos Prefix Correctness
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:11-18; python/larch/issue/oos_filer.py:15-25; skills/issue/SKILL.md:24-39
- **Concern**: Auto-prefixing from only the first OOS heading is too broad and can misclassify non-OOS bodies as OOS.. Scenario: A copied snippet or ordinary issue body that starts with `## Out-of-Scope Observation` would get `[OOS]` even though the caller did not mean to file an OOS issue, which changes the title and can affect downstream routing and dedup behavior.
- **Proposed resolution**: Match the full fixed OOS wrapper shape, or another explicit sentinel, before injecting `[OOS]`.
