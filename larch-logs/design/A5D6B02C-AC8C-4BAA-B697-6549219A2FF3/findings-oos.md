### OOS_1: [SCOPE-REDUCTION] Unconditional pre-fix on every `reship` exceeds the autonomous fix-handoff contract
- **Description**: [SCOPE-REDUCTION] Unconditional pre-fix on every `reship` exceeds the autonomous fix-handoff contract. Scenario: The binding scope requires fetch+rebase before the main agent applies a fix (`ci-fix`). Many `reship` paths are driver retries with no repo edits (`exit 0` non-OK, transient infra, phase14 no-checks retry). Forcing pre-fix on all reships adds fetch/rebase work and conflict surface without edit benefit.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md
- **Phase**: design



