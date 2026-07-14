### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: code-quality
- **Location**: Makefile:47-88
- **Concern**: [SCOPE-REDUCTION] Separate focused lint and test Make targets are convenience scope. Scenario: The direct `python3 python/cli.py lint kv-codec` command, focused pytest invocation, and `py-lint-checks-fast` integration already make the feature runnable and enforced. Extra aliases enlarge the Makefile and maintenance surface.
- **Proposed resolution**: Retain the fast-lint integration and guarded baseline regeneration, but omit new standalone focused lint and test targets.
