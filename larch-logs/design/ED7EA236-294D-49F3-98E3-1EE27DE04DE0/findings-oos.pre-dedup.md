### OOS_1:
- **Description**: Secondary implement reference docs still name ship-pr.sh or lint-fix-loop.sh as live callers. Scenario: Operator/docs drift after retirement; likely caught by planned git grep but not listed as explicit edit surfaces
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/scripts/write-final-report.md:67 / skills/implement/references/stall-recovery.md:100
- **Phase**: design

### OOS_1:
- **Description**: Makefile-only harness exclusion list still names scripts slated for deletion. Scenario: Stale entries after harness removal are harmless if agent-lint ignores missing paths, but they add maintenance noise
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: agent-lint.toml:500-513
- **Phase**: design

### OOS_2:
- **Description**: Implementer prompts still tell coders not to run `scripts/relevant-checks.sh`. Scenario: Minor doc drift after script deletion; does not affect runtime
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: code-quality
- **Location**: agents/codex-implementer.md:220 / agents/cursor-implementer.md:224
- **Phase**: design

### OOS_1:
- **Description**: Plan removes --codex-add-dir comparison but does not rewrite the symlink-mirror bullet that still cites --codex-add-dir validation. Scenario: Future edits to launch-review may follow stale parity guidance after the flag is removed
- **Reviewer**: Cursor-dyn-security-boundary-reviewer
- **Severity**: nit
- **Focus area**: architecture
- **Location**: .claude/rules/external-tool-launcher-parity.md:28
- **Phase**: design

