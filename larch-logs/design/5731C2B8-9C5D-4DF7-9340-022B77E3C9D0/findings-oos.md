### OOS_1: Conflict-resolution prose still routes post-rebase reassessment through legacy `NEXT_ACTION=guidelines-assessment`
- **Description**: Conflict-resolution prose still routes post-rebase reassessment through legacy `NEXT_ACTION=guidelines-assessment`. Scenario: After a successful `ship_pr_pre_push` rebase continue, operators following conflict-resolution.md are told the next ship relaunch will request fresh `guidelines-assessment` on `HEAD`/diff change, contradicting the scoped once-per-run adapter semantics and reintroducing per-alias orchestration outside the eight approved surfaces
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/references/conflict-resolution.md:85
- **Phase**: design



### OOS_2: Conflict-resolution prose still promises guidelines-assessment reassessment on every HEAD change
- **Description**: Conflict-resolution prose still promises guidelines-assessment reassessment on every HEAD change. Scenario: After Piece 4 ships, conflict-resolution still tells the orchestrator that the next step-8-ship.sh relaunch will request NEXT_ACTION=guidelines-assessment whenever HEAD changed, contradicting scoped once-per-run reuse and the updated Step 8 adapter route outside this piece's eight surfaces
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/references/conflict-resolution.md:85
- **Phase**: design



