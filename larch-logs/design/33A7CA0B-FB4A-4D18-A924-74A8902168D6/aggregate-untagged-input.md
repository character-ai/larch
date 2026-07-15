### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_unreachable_branch.py
- **Concern**: Occurrence-baseline Finding fields are not pinned in detect() adaptation. Scenario: With occurrence_baseline=True, engine validation requires every Finding to carry qualified_symbol, pattern_name, and occurrence together. The plan only says to adapt hits and preserve rendered lines; the equivalence mapper sets message text with cond= but omits pattern_name and occurrence. A port that follows that shape fails at _validate_finding before baseline comparison or CLI output.
- **Proposed resolution**: In detect(), set pattern_name to the normalized condition string, occurrence to the per-qualified-symbol index, and qualified_symbol to the legacy value; keep the existing message format. Add a test that adapted findings pass engine validation and round-trip through the Piece 1 normalized_condition codec.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_unreachable_branch.py
- **Concern**: strict_stale run_rule wiring is still implicit. Scenario: Legacy check mode exits 2 on any stale baseline row. Engine defaults strict_stale=False and only warns on stale rows. The plan states strict stale behavior in Failure modes and tests stale exit, but the REWRITTEN main() section does not pin strict_stale=not bool(parsed.write) the way lint_markdown_heading_fence_state.py does. An implementer can pass tests only after manual discovery and still ship warning-only stale handling.
- **Proposed resolution**: In thin main(), call run_rule with strict_stale=not bool(parsed.write) on check runs, matching the markdown port. Add a RULE contract assertion or CLI test that stale rows exit 2 while write mode stays non-strict.

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_unreachable_branch.py
- **Concern**: Pathspecs alone do not preserve legacy test/support exclusions. Scenario: The plan pins `python/larch/*.py` and `python/larch/**/*.py` pathspecs and says to preserve test/support/symlink exclusions, but it never requires a `LintRule.source_filter` like the markdown port. `git ls-files` with those pathspecs still returns tracked `python/larch/test_*.py`, `conftest.py`, and support files. `test_scope_excludes_tests` and the planned production-path filtering case would fail or widen findings.
- **Proposed resolution**: Add a repo-relative pre-load filter on `RULE` (reuse the existing `is_exempt_path` / excluded-dir predicate scoped to `python/larch/...`) and keep the planned CLI test that `python/cli.py` stays out of scope.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_unreachable_branch.py
- **Concern**: Engine occurrence identity fields are not pinned in `detect()`. Scenario: With `occurrence_baseline=True`, `engine.py` requires each finding to carry `qualified_symbol`, `pattern_name`, and `occurrence` together. The plan only says to adapt hits to engine findings and mentions normalized conditions in messages/tests, but it never says to map `normalized_condition` into `Finding.pattern_name`. A message-only adapter fails validation before baseline comparison.
- **Proposed resolution**: In `detect()`, emit engine `Finding` values with `qualified_symbol`, `occurrence`, and `pattern_name=<normalized_condition>`; keep the existing rendered message/cond text unchanged.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_unreachable_branch.py
- **Concern**: Check-mode syntax and stale wiring are still unspecified. Scenario: Legacy check mode exits 2 on malformed Python (`test_malformed_source_exits_2`) and on stale baseline rows (`test_baseline_schema_and_stale`). Engine defaults are `syntax_policy="fail"` (exit 1 with a syntax finding) and `strict_stale=false` (stale rows warn only). The plan cites shared engine syntax handling and strict-stale failure but does not pin the markdown-port wiring.
- **Proposed resolution**: Pin `RULE.syntax_policy="raise"`, `allow_inline_suppression=False`, and `occurrence_baseline=True`; in `main()`, pass `strict_stale=not bool(parsed.write)` to `run_rule`, matching `lint_markdown_heading_fence_state.py`.

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/lint/lint_unreachable_branch.py
- **Concern**: Production discovery preserves test/support exclusions in prose but only pins `python/larch` pathspecs. Scenario: `git ls-files` with `python/larch/*.py` and `python/larch/**/*.py` still returns tracked `test_*.py`, `conftest.py`, and support fixtures under `python/larch`. Legacy `_collect_all` excludes them via `iter_source_files`; the markdown port excludes them with `LintRule.source_filter`. Without the same filter on the engine-backed production path, scope widens and findings or baseline identities can drift. Planned production-path tests only exclude `python/cli.py` / `python/bootstrap.py`, and `test_scope_excludes_tests` exercises the compatibility `iter_source_files` adapter only.
- **Proposed resolution**: In the REWRITTEN `LintRule`, add a pre-load `source_filter` matching legacy exclusions (reuse or narrow `is_production_source_path` / `is_exempt_path`). Extend production CLI discovery tests to assert tracked `test_*.py` and support files under `python/larch` are not scanned.

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:276-327
- **Concern**: Tracked symlink exclusion cannot be preserved by the proposed engine-backed rule. Scenario: The legacy iterator skips a tracked `python/larch/*.py` symlink, while engine discovery rejects it with exit 2 before a rule path filter can exclude it. This changes the lint’s existing behavior despite the plan requiring symlink exclusion preservation.
- **Proposed resolution**: Add a safe rule-specific discovery mechanism that skips these legacy-excluded symlinks before engine filesystem validation, and cover a tracked in-scope symlink in the port tests.
