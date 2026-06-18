### FINDING_2:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/review_and_fix.py:1386-1433
- **Concern**: [SCOPE-REDUCTION] Plan replaces a targeted failure cleanup with a new snapshot-mode state machine. Scenario: The bug needs failed-coder and failed-commit cleanup plus waterfall continuation. The proposed head_untracked attempt patches, lazy baselines, verification logs, and broad test matrix expand the change to 455 lines and add new recovery semantics not required for the reported staged residue.
- **Proposed resolution**: Reduce to one cleanup helper called from the coder-false, commit-failure, and submodule-violation paths: restore tracked coder edits to HEAD, remove untracked paths outside the pre-coder baseline, unstage before any rc=2 return, and keep tests to failed coder, failed commit, and waterfall fallback.
