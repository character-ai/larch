### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:74-75
- **Concern**: UPDATED target names nonexistent `python/larch/cli.py` instead of the real dispatcher file.. Scenario: If followed literally, the new `shared-convention-regex` command is never registered, so the lint cannot be invoked from `python/cli.py`.
- **Proposed resolution**: Change the UPDATED path to `python/cli.py` and keep the registry edit there.



### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_shared_convention_regex.py:58-66
- **Concern**: Global owner allowlist skips the other convention owner. Scenario: If title_match.py adds a G-/I- heading regex, or architectural_guidelines.py adds a module-level "[BUG] in:title" selector, the proposed scan skips the whole file and the hard ban no longer enforces the per-convention owner contract.
- **Proposed resolution**: Do not exclude both owner modules globally. Scan owner files and suppress only the convention owned by that specific file; keep only the lint implementation self-exclusion global.



### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/issue/test_learn_from_bugs.py:89-94
- **Concern**: Parity test still lacks reader accepted-population assertion. Scenario: GUIDELINE_HEADING_RE and coverage_index can agree while parse_guideline_entries or parse_invariant_entries drifts to a different matcher or preprocessing path, so the reader/indexer divergence this feature fixes would not fail the test.
- **Proposed resolution**: For the same fixture, derive the reader (id, title) population from parse_guideline_entries and parse_invariant_entries output and assert it equals the expected shared-constant population and coverage_index output.



