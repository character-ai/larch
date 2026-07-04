### OOS_1: Ephemeral dynamic scout reviewers still lack readability wiring
- **Description**: Ephemeral dynamic scout reviewers still lack readability wiring. Scenario: `_dynamic_agent_body` builds one-off `reviewer-dyn-*` prompts with scout `prompt_body` only and never pulls agent templates or readability-style. Those slots still emit user-facing finding text in Step 5 when scouting succeeds.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/larch/review/review_dispatch_panel.py:188-223
- **Phase**: design



