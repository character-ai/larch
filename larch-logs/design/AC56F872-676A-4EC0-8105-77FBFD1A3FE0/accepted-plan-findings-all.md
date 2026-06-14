### FINDING_2: Recovery prescription conflicts with adjacent polling-loop ban
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: important
- **Concern**: The proposed premature-notification recovery text tells orchestrators to re-launch `until <condition>; do sleep N; done`, which matches the `for`/`while`/`until` + `sleep` Bash polling-loop shape already banned in the same rules (AGENTS.md Conventions, `/implement` NEVER #8, `/design` anti-halt / immediate-background guidance). A literal reader sees conflicting instructions: avoid polling loops vs. use one after a premature empty notification. That can block the sanctioned one-shot recovery path or be read as voiding the ban.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Clarify in the appended NEVER #8 text that orchestrator turn polling and Monitor are banned, while exactly one re-launched background completion waiter (until condition; do sleep N; done) is the sanctioned recovery path when task-notification fires prematurely
  - From Codex-Innovation: Revise the new sentence to make this a narrow explicit exception to the polling-loop ban after a proven premature notification, or describe it as a single immediate-background completion waiter while preserving the “never Monitor” rule.



### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-anti-polling-rule.sh:51-65
- **Concern**: Harness pins only the Monitor-ban headline on implement/design, not premature-notification recovery contract. Scenario: The issue requires both an explicit Monitor prohibition and narrow single-waiter recovery on skills/implement/SKILL.md and skills/design/SKILL.md. Planned checks grep only NEVER use the Monitor tool anywhere within the orchestrator. An edit could drop the premature-empty-notification recovery text (only sanctioned exception, Do NOT fall back to Monitor, exactly one waiter) while tests still pass, leaving the BC8DDA64 failure mode unenforced on two of three prose surfaces
- **Proposed resolution**: Add implement/design check() literals for the recovery phrases (e.g. only sanctioned exception to the Bash polling-loop ban is one re-launched immediate-background completion waiter and Do NOT fall back to Monitor), mirroring the AGENTS.md assertion already in the plan


