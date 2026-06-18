### FINDING_3: `head_untracked` cleanup step order inconsistent between Approach and Files
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Concern**: Head-untracked cleanup step order is inconsistent within the plan. The Approach specifies unstage, restore tracked, then delete untracked; the Files section specifies delete untracked then restore tracked. If a coder creates a new untracked file under a tracked directory that restore/checkout recreates, order-dependent residue or failed verification can leave a dirty tree on rc=2 stall paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Pick one order in the plan and align both sections; prefer unstage, restore attempt-baseline tracked state, then remove attempt untracked deltas (matches Approach)


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected (latent-rerouted)

### OOS_1:
- **Description**: `coder-main-agent-required` prose still describes only edit exhaustion (and misorders Codex/Cursor) and does not mention commit failures now waterfall to rc=4 after clean cleanup. Scenario: Operators reading the branch doc may still expect commit-hook failures to stall as `coder-failed` rather than hand off to main-agent apply
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/implement/references/step5-review-branches.md:25-27
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

