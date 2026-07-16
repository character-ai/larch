### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_status_routing_truthiness.py:LintRule
- **Concern**: The LintRule contract omits require_baseline=True. Scenario: G-Enf-2 expects a committed reason-bearing baseline for every ratchet. Without require_baseline, a missing baseline file plus zero live findings exits 0, so CI can pass before python/status-routing-truthiness-baseline.json exists.
- **Proposed resolution**: Pin require_baseline=True on the RULE dataclass, matching lint_unreachable_branch.py, and add a test that a missing baseline file exits 2 even when the live scan is clean.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_status_routing_truthiness.py:PATHSPECS
- **Concern**: Scan pathspecs omit the shallow python/larch/*.py glob. Scenario: Engine-backed larch lints use ("python/larch/*.py", "python/larch/**/*.py"). A single ** pathspec can skip direct children such as python/larch/cli.py, leaving shallow production modules unscanned.
- **Proposed resolution**: Pin PATHSPECS to both globs like lint_tmpdir_arg_env_fallback.py and assert them in tests.



### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/lint/lint_status_routing_truthiness.py
- **Concern**: The LintRule contract omits require_baseline=True.. Scenario: The nearest engine-backed template (lint_unreachable_branch.py) sets require_baseline=True and tests missing-baseline exit 2. With the default False, a missing python/status-routing-truthiness-baseline.json yields exit 0 on a clean scan, so the ratchet can run green without the committed grandfather baseline the issue requires. Pin require_baseline=True on RULE; add test_rule_contract_flags and test_clean_scan_without_baseline_exits_2 mirroring test_lint_unreachable_branch.py. Also set allow_inline_suppression=True explicitly (unreachable uses False with detector-local suppression; this rule needs engine-managed pragmas).
- **Proposed resolution**: 



### FINDING_4:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/lint/engine.py:1037-1064
- **Concern**: Occurrence baseline field choice is not enforced. Scenario: The plan selects normalized_condition, but the shared parser accepts pattern_name rows too and collapses both forms into one occurrence type, allowing a mixed baseline despite the required single consistent identity field.
- **Proposed resolution**: Add rule-aware baseline schema validation that rejects pattern_name or mixed rows for this normalized_condition rule, and test those rejection cases.



