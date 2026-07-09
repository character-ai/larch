### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:5-7,59-77
- **Concern**: [SCOPE-REDUCTION] Do not inherit the sibling lints' owner-module skips; keep the full production `python/**/*.py` scope in view.. Scenario: If the implementation copies `lint_subprocess_via_runner.iter_source_files` or `lint_env_via_config_constant.iter_source_files` verbatim, `python/larch/core/config.py:353` and any similar owner files stay outside the ratchet, so existing suppression debt and future bare suppressions there will still pass locally and in CI.
- **Proposed resolution**: Build a local iterator that only excludes tests, helper filenames, symlinks, cache, vendored, and virtualenv dirs. Do not carry over the `proc.py` or `config.py` self-exclusion from sibling lints.
