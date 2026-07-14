### FINDING_5:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/support/shell_fixtures.py
- **Concern**: [SCOPE-REDUCTION] Prefer baked repo_root over new runtime env wire. Scenario: G-Cfg-1 / G-Fix-1: harness lessons baked repo_root into fake cli.py instead of requiring per-invocation LARCH_TEST_REAL_REPO_ROOT. Adding a new env literal duplicates wire surface without config.py ownership.
- **Proposed resolution**: In the plugin-tree Approach, mandate embedding str(repo_root()) in generated delegate stubs; do not add LARCH_TEST_REAL_REPO_ROOT unless a later piece proves runtime override is required.
