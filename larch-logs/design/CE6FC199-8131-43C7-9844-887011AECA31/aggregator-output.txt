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

### FINDING_3: Baseline identity field is not restricted
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: The shared baseline parser accepts both `normalized_condition` and `pattern_name` rows, so this rule could accept mixed or incorrectly keyed baseline identities despite selecting `normalized_condition`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add rule-aware baseline schema validation that rejects pattern_name or mixed rows for this normalized_condition rule, and test those rejection cases.
