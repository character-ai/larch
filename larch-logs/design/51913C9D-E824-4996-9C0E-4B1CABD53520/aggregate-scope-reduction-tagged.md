### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:184-188
- **Concern**: [SCOPE-REDUCTION] Broad Python validation conflicts with changed-files-only constraint. Scenario: The plan already lists focused pytest coverage for the new ledger, git helper, and registry import. Requiring make py-lint and make py-test runs whole-tree pylint, pyright, and pytest despite AGENTS.md limiting local lint/test to changed files and leaving full sweeps to CI.
- **Proposed resolution**: Drop the broad make py-lint and make py-test step; keep the focused pytest commands and use the repo's changed-file validation path only if a general changed-file check is needed.
