### OOS_1: Same AskUserQuestion timeout-to-default pattern exists outside /design
- **Description**: Same AskUserQuestion timeout-to-default pattern exists outside /design. Scenario: Implement run logs show operators not responding within a turn and the run proceeding autonomously. Issue scope is /design only; parity would touch implement references and closure.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:408-408
- **Phase**: design



### OOS_2: [OUT_OF_SCOPE] Same timeout-as-terse-answer pattern exists in `/implement` Q/A loops
- **Description**: [OUT_OF_SCOPE] Same timeout-as-terse-answer pattern exists in `/implement` Q/A loops. Scenario: `/implement` also accepts `AskUserQuestion` returns in Step 2.3 without a no-response re-ask rule. Out of issue scope, but operators may expect parity after this fix.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:359-374
- **Phase**: design



### OOS_3: Uncapped same-prompt retries may loop 60s waits indefinitely within one long turn
- **Description**: Uncapped same-prompt retries may loop 60s waits indefinitely within one long turn. Scenario: Re-firing without yielding can stack repeated wait windows and burn context before the operator returns, especially on Gate C approval prompts.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md (proposed anti-pattern rule 6)
- **Phase**: design



### OOS_4: Design Mindset still says muscle memory for the six rules while anti-patterns currently lists five rules
- **Description**: Design Mindset still says muscle memory for the six rules while anti-patterns currently lists five rules. Scenario: Minor stale count until rule 6 lands; no behavioral impact once rule 6 is added
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/SKILL.md:67
- **Phase**: design



