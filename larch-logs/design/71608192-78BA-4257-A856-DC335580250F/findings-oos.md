### OOS_1: /review skill Step 2 prose still documents Codex-first TRIVIAL singles and HARD default-role pairs
- **Description**: /review skill Step 2 prose still documents Codex-first TRIVIAL singles and HARD default-role pairs. Scenario: Runtime dispatch moves to Cursor-first TRIVIAL with a Codex luna floor and tier-specific panel models, but the standalone /review skill text was not in the plan file list; operators and subagents following the skill will mis-predict panel shape
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/review/SKILL.md:49
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Changing CLAUDE_CI_FIX_MODEL also changes launch-claude-lint-fix
- **Description**: [OUT_OF_SCOPE] Changing CLAUDE_CI_FIX_MODEL also changes launch-claude-lint-fix. Scenario: The shared constant is reused by the lint-fix launcher, so the proposed [1m] default would silently alter an unrelated fixer waterfall the plan does not scope.
- **Reviewer**: Codex-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/core/config.py:535-543
- **Phase**: design



