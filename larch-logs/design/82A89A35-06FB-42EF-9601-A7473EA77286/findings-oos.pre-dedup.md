### OOS_1:
- **Description**: Unifying Step 2b display drops the drafter model from the human-visible large-plan header. Scenario: After the change, large successful drafts show ## Implementation Plan instead of ## Plan Summary (drafter: MODEL); model remains only in the machine success line. Operators lose an at-a-glance model label in chat unless they read the breadcrumb
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:1140-1148
- **Phase**: design

### OOS_2:
- **Description**: Plan fixes only the primary Claude voter Agent-tool line; replacement-voter prose stays stale. Scenario: Lines 149 and 167 still say launch Claude replacements via the Agent tool, while dispatch-plan-voters.sh uses --no-fallback and does not back-fill failed externals with Claude voters (#3207). Readers can still misunderstand replacement behavior after the one-line fix
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/shared/voting-protocol.md:149-169
- **Phase**: design

