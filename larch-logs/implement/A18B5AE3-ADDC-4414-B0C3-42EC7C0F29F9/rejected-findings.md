### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Missing ignore-interim-output guard on immediate-background launch ack
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: The explicit ignore-the-interim-output-suggestion guard was removed from the immediate-background wait rule. After background launch the Bash ack suggests checking interim output; without a named counter-instruction an orchestrator may read partial task output before notification or sentinel confirmation, burning turns and risking premature parsing despite the general do-not-read ban.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: WAIT/DONE no longer equates DONE with terminal-sentinel presence
- **Reviewer(s)**: dyn-dyn-wait-contract
- **Severity**: important
- **Concern**: The WAIT/DONE paragraph no longer equates `DONE` with terminal-sentinel presence (`When the terminal sentinel is present (\`DONE\`)` became `On \`DONE\``). Call sites such as `skills/design/SKILL.md:180` still mix probe `WAIT` with sentinel `When present`, so the shared anchor no longer states that `DONE` means the sentinel exists and `WAIT`/absent means yield. That raises the risk of parsing or advancing on premature stdout instead of confirmed completion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-wait-contract: Restore explicit equivalence, e.g. `When the terminal sentinel is present (\`DONE\`), proceed… On probe \`WAIT\` or absent sentinel, yield without \`ps\` polling.`


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

