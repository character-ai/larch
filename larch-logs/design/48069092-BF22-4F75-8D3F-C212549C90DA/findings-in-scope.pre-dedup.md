### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/design-background-wait.md:29-31
- **Concern**: Safe-compression merge guidance conflicts with dual harness-pinned waiter-ban literals. Scenario: The plan tells implementers to merge adjacent sentences that repeat the same guard, but lines 29 and 31 intentionally use two forms: harness `check` requires exact `NEVER launch a background recovery waiter` (test-implement-anti-polling-rule.sh:225-226) while line 31 keeps the longer `Do not launch a background recovery waiter such as…` variant. Merging them per safe-compression drops the NEVER-prefixed substring and CI fails even though semantics look preserved. The edge-case waiter-ban warning is too generic to block that edit.
- **Proposed resolution**: Add an explicit safe-compression carve-out: never merge the line-29 NEVER waiter ban with the line-31 `Do not launch…` example, and add `NEVER poll `.step3-review-result.env` with a sleep loop.` and `NEVER launch a background recovery waiter` to the protected-literal bullet list (harness also enforces the poll literal exactly once at lines 216-223).



### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/design-background-wait.md
- **Concern**: Plan omits harness check_context anchor and two-line window constraints for several anti-polling literals. Scenario: scripts/test-implement-anti-polling-rule.sh uses check_context, not file-wide grep, for When task output is empty, call no tool (within two lines after After the background launch ack) and end the turn without probing (within two lines after Foreground terminal-sentinel probe). The plan lists those strings as protected but not their anchor placement. Cross-section dedupe or density edits can keep the substrings elsewhere and still fail CI.
- **Proposed resolution**: Extend the protected-literal section with an anchor layout table copied from the harness: After the background launch ack plus two lines must retain When task output is empty and call no tool; Foreground terminal-sentinel probe plus two lines must retain end the turn without probing; keep the After the background launch ack anchor phrase byte-identical.



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/design-background-wait.md
- **Concern**: Safe-compression merge guidance can drop the harness-exact NEVER launch a background recovery waiter substring. Scenario: The plan allows merging adjacent sentences that repeat the same guard. The file has two waiter-ban phrasings; only NEVER launch a background recovery waiter is harness-pinned (scripts/test-implement-anti-polling-rule.sh:225-226). Consolidating into the Do not launch a background recovery waiter such as variant preserves semantics but removes the exact literal and breaks CI.
- **Proposed resolution**: Add an explicit carve-out under safe compression: never merge or paraphrase away the standalone NEVER launch a background recovery waiter sentence; keep it as its own harness-exact line distinct from the longer Do not launch example.



