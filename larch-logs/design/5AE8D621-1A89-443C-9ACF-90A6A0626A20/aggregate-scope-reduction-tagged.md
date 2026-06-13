### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/migration_lint.py:60-82
- **Concern**: [SCOPE-REDUCTION] Plan limits bare-basename linting to .claude/skills/**/*.md, but the issue asks make lint-retired-scripts to catch bare filename occurrences in markdown prose. Scenario: Bare retired script names in other markdown prose, such as docs/*.md or skills/*.md, still pass the lint after this PR
- **Proposed resolution**: Remove the .claude/skills-only eligibility guard. Apply the basename matcher to markdown prose generally, using non-path boundaries and # lint-ignore for legitimate historical prose.
