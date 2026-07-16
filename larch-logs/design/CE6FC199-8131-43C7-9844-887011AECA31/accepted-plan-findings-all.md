### FINDING_3: Suppression token must match documented pragma
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The planned token `status-routing-truthiness` conflicts with the documented and required `lint-status-routing-truthiness` pragma, so valid suppressions would not be recognized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Pin rule_id and suppression_token to lint-status-routing-truthiness (matching unreachable-branch and markdown-heading-fence-state). Keep the CLI subcommand status-routing-truthiness. Set RuleCli error_label to lint-status-routing-truthiness and align docs/linting.md with that token.
  - From Cursor-Pragmatic: Set SUPPRESSION and LintRule.suppression_token to lint-status-routing-truthiness (matching unreachable-branch and tmpdir-arg-env-fallback); align the NEW module bullet and docs with that token


### FINDING_4: Baselined findings need the required warning path
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: The shared CLI path currently suppresses matching baseline rows silently, so the required non-failing warning output cannot be produced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add an opt-in shared-engine warning path for matching occurrence baseline rows, enable it for this rule, and test the clean exit plus warning output


### FINDING_7: Tracked symlinks require discovery-level exclusion
- **Reviewer(s)**: Codex-dyn-Status Ast Semantics
- **Severity**: minor
- **Concern**: A string-only source filter cannot exclude tracked Python symlinks before engine discovery, so an in-scope symlink may fail with exit 2 instead of being ignored.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Status Ast Semantics: Add the minimal engine discovery opt-out needed to skip symlinks for this rule, list engine.py in the plan, and test a tracked in-scope symlink is ignored while real required inputs still fail closed


### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-Status Ast Semantics
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_status_routing_truthiness.py:LintRule
- **Concern**: [SCOPE-REDUCTION] suppression_token omits required lint- prefix. Scenario: Plan sets rule ID and suppression_token to status-routing-truthiness, but scope/docs require # lint-status-routing-truthiness: ok. engine._scan_source matches rule.suppression_token literally (engine.py:1434-1435, _apply_inline_suppressions). Wrong token makes every same-line suppression a no-op while empty-reason tests still pass via ScanError.
- **Proposed resolution**: Set SUPPRESSION/RULE_ID/suppression_token to lint-status-routing-truthiness; keep CLI subcommand status-routing-truthiness per lint_unreachable_branch.py:30-31,71 and cli.py:600.


### FINDING_1: Missing required baseline enforcement
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: major
- **Concern**: `RULE` does not require a baseline. A clean scan can therefore exit 0 when `python/status-routing-truthiness-baseline.json` is missing, allowing the ratchet to pass without its committed reason-bearing baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin require_baseline=True on the RULE dataclass, matching lint_unreachable_branch.py, and add a test that a missing baseline file exits 2 even when the live scan is clean.


### FINDING_2: Incomplete scan pathspecs
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: `PATHSPECS` omits the shallow `python/larch/*.py` glob. Using only the recursive pathspec may skip direct child modules such as `python/larch/cli.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin PATHSPECS to both globs like lint_tmpdir_arg_env_fallback.py and assert them in tests.


