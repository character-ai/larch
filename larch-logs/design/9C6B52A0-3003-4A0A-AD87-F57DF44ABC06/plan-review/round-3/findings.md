### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: nit
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:60-71; scripts/test-rebase-push-keep-on-conflict.sh:64-83
- **Concern**: New standalone rebase-push fetch harness adds avoidable SIMPLE-tier surface. Scenario: The existing keep-on-conflict harness already drives rebase-push.sh --no-push through the fetch/rebase flow, so adding a new .sh, .md, Makefile target, shard entry, and agent-lint exclusions expands maintenance surface for one narrow fetch-retry assertion
- **Proposed resolution**: Extend scripts/test-rebase-push-keep-on-conflict.sh with the transient-once and persistent-fetch-failure cases, update its sibling md, and drop the NEW harness plus Makefile and agent-lint additions

### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-predicate-scope-drift, Codex-dyn-predicate-scope-drift
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-lib-net.sh:78-100
- **Concern**: Planned signature coverage adds positives only and does not pin adversarial near-misses for the new broad DNS/reset entries. Scenario: Current negatives are only empty and generic error, and the plan only asks for fixtures for the new transient signatures. A bare substring implementation of no such host could classify adjacent non-network gh or check output such as no such hosted runner, while the planned test-merge-pr pending/failing case would miss that if its stub avoids the new substrings.
- **Proposed resolution**: Add targeted negative fixtures beside the new positives for lookup/no such host/Connection reset by peer, especially a lowercase no such hosted near-miss and a lookup line without resolver/no such host shape; narrow the bare no such host pattern if the negative exposes overmatch.
