## Decision 1: Scope is exactly as specified in issue body
- **Question**: Are there any scope ambiguities or hidden constraints?
- **Resolution**: No. Issue #2596 enumerates files to delete (5 round-trip-detect files), files to modify (tracking-issue-write, implement SKILL.md, implement-finalize, Makefile, ship-pr.sh, agent-lint.toml, docs/linting.md, test-step-8a-changelog.sh, test-implement-finalize.sh, test-false-positive-keywords.sh), and provides 6 explicit acceptance criteria. The "Why delete rather than tighten" section rules out the only plausible alternative.
- **Source**: codebase (verified 16 files containing round-trip references; matches issue scope)
