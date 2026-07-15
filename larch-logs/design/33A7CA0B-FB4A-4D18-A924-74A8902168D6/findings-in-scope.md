### FINDING_1: Occurrence-baseline identity fields are not pinned
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The detector adaptation does not explicitly populate the required occurrence-baseline identity fields. With `occurrence_baseline=True`, each finding must carry `qualified_symbol`, `pattern_name`, and `occurrence`; a message-only adapter fails engine validation before baseline comparison.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In detect(), set pattern_name to the normalized condition string, occurrence to the per-qualified-symbol index, and qualified_symbol to the legacy value; keep the existing message format. Add a test that adapted findings pass engine validation and round-trip through the Piece 1 normalized_condition codec.
  - From Cursor-Pragmatic: In `detect()`, emit engine `Finding` values with `qualified_symbol`, `occurrence`, and `pattern_name=<normalized_condition>`; keep the existing rendered message/cond text unchanged.

### FINDING_2: Legacy check-mode failure semantics are not fully pinned
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The plan does not explicitly wire legacy syntax-error and stale-baseline behavior through the engine. Engine defaults can produce a syntax finding with exit 1 and warning-only stale handling, whereas legacy check mode requires exit 2 for both cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In thin main(), call run_rule with strict_stale=not bool(parsed.write) on check runs, matching the markdown port. Add a RULE contract assertion or CLI test that stale rows exit 2 while write mode stays non-strict.
  - From Cursor-Pragmatic: Pin `RULE.syntax_policy="raise"`, `allow_inline_suppression=False`, and `occurrence_baseline=True`; in `main()`, pass `strict_stale=not bool(parsed.write)` to `run_rule`, matching `lint_markdown_heading_fence_state.py`.

### FINDING_3: Production discovery does not preserve legacy exclusions
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The proposed pathspecs alone still discover tracked test, support, and other legacy-excluded files under `python/larch`, widening scan scope and potentially changing findings or baseline identities.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add a repo-relative pre-load filter on `RULE` (reuse the existing `is_exempt_path` / excluded-dir predicate scoped to `python/larch/...`) and keep the planned CLI test that `python/cli.py` stays out of scope.
  - From Cursor-Requirements: In the REWRITTEN `LintRule`, add a pre-load `source_filter` matching legacy exclusions (reuse or narrow `is_production_source_path` / `is_exempt_path`). Extend production CLI discovery tests to assert tracked `test_*.py` and support files under `python/larch` are not scanned.

### FINDING_4: Tracked symlink exclusion is incompatible with current engine discovery
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: A tracked in-scope symlink may be rejected by engine discovery before a rule-level path filter can exclude it, changing the legacy linter’s behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a safe rule-specific discovery mechanism that skips these legacy-excluded symlinks before engine filesystem validation, and cover a tracked in-scope symlink in the port tests.

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_unreachable_branch.py
- **Concern**: [SCOPE-REDUCTION] Production exclusion filter is unspecified for git discovery. Scenario: Pathspecs python/larch/**/*.py still match tracked test_*.py, conftest.py, and support filenames under python/larch. Legacy iter_source_files drops them via is_exempt_path; engine discovery uses git ls-files plus optional source_filter. The plan says to preserve exclusions but does not wire a LintRule source_filter (markdown uses is_production_source_path). A tracked exempt file would be scanned and could change live identities and baseline results.
- **Proposed resolution**: Reuse the existing is_exempt_path logic as a repo-relative source_filter on LintRule, mirroring lint_markdown_heading_fence_state.py. Extend the engine-backed CLI test to git-track an exempt filename and assert it is skipped while eligible python/larch files are scanned.
