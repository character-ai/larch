### OOS_1:
- **Description**: Plan mirrors the default into write-session-env for /research, but /research Step 0 runs session-setup without --write-session-env and calls run-external-agent.sh directly from phase markdown. Scenario: Research validation/research lanes never inherit the production default; only /design (source-env export) and fully wired /implement paths benefit
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/research/SKILL.md:125 / skills/research/references/validation-phase.md:96
- **Phase**: design

