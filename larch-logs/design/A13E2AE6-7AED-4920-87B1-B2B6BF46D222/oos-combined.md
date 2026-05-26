### OOS_1:
- **Description**: Comment says drop-bump walks from HEAD and bump must remain at HEAD; after fix CHANGELOG may sit above bump. Scenario: Misleading maintainer mental model when debugging rebump
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: .claude/skills/bump-version/scripts/apply-bump.md:40-41
- **Phase**: design

### OOS_2:
- **Description**: Edit-in-sync requires conflict-resolution.md updates for trivial-file behavior; plan does not touch it. Scenario: Docs still imply single amended bump+CHANGELOG commit only
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/drop-bump-commit.md:40-48
- **Phase**: design

### OOS_3:
- **Description**: Step 8a failure strings still say amend after separate commit. Scenario: Operator logs say amend failed though behavior is a new commit
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/implement-finalize.sh:780-781
- **Phase**: design

