### OOS_1:
- **Description**: The plan drops the prompt-side scout-manifest clear that currently runs immediately after findings are applied and before the LLM duplicate sweep.. Scenario: Stale scout-plan-manifest.json may linger through steps 2-5 until postplan clears it; unlikely to break Gate B but differs from today's ordering.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:154
- **Phase**: design

