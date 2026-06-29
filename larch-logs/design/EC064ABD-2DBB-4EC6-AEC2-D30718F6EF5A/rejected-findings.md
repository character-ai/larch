### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:121-130
- **Concern**: [SCOPE-REDUCTION] Drop the dedicated `test-lint-tier1a-size` Make target and its `.PHONY` entry. Scenario: The plan already runs `python3 -m pytest python/test_lint_tier1a.py -q` and `make py-test`, so this wrapper adds a second entry point without protecting any new risk-bearing path.
- **Proposed resolution**: Keep `lint-tier1a-size` and the new pytest file, but remove `test-lint-tier1a-size` from the Makefile and from the focused-check list.

