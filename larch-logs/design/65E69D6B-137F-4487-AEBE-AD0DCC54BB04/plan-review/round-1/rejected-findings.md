### [Plan Review] FINDING_5

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/test-plan-review-scope-anchor.sh:77-99
- **Concern**: Dedicated end-to-end harness duplicates surfaces already extended elsewhere. Scenario: Plan adds test-plan-review-scope-anchor.sh plus Makefile/agent-lint siblings while also extending test-tally-plan-review.sh, test-plan-review-prompt.sh, and test-render-voter-prompt.sh for the same tally and prompt contracts; ~520 added lines already buy coverage
- **Proposed resolution**: Fold tally YES>=1 scope-cut cases into test-tally-plan-review.sh and keep prompt byte-equality in the existing prompt harnesses; drop the new harness/Makefile target unless it adds a unique assertion


