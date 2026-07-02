### OOS_1: SKILL.md still enumerates Gate C option sets inline after `approval-gates.md` shrinks to renderer delegation
- **Description**: SKILL.md still enumerates Gate C option sets inline after `approval-gates.md` shrinks to renderer delegation. Scenario: Step 4b prose still lists cap-gated options (`Approve` / `See full plan` / `Discuss further` / `Re-run review panel`) and panel-failed relabel behavior inline while the plan only moves prompt authority into Python plus shrunk `approval-gates.md`. Implementers can follow SKILL prose instead of `design render-gate`, leaving eager closure incomplete and risking prompt drift on resume paths.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:547
- **Phase**: design



