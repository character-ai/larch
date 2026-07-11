### FINDING_4: Rewrite durable handoff prose to enforce one combined adapter route
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The durable handoff paragraph still describes independent legacy relaunches and main-agent consumption of materialized assessment diffs. That contradicts the single combined adapter invocation and one post-validation ship relaunch, leaving an inline-authorship escape hatch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit `ship-pr-exit-matrix.md` task to rewrite the durable handoff paragraph so all three assessment tokens normalize to `NEXT_ACTION=assessments`, invoke the combined adapter once, validate its envelope, and relaunch ship once; remove independent back-compat relaunch and materialized-diff authorship language
  - From Cursor-Requirements: Rewrite the durable handoff paragraph to state that all assessment tokens normalize to NEXT_ACTION=assessments, the adapter owns assessment work from existing materialization inputs, legacy aliases do not relaunch independently, and only one post-validation step-8-ship.sh relaunch is allowed. Add a harness negative assertion against relaunch independently and main-agent materialized-diff consumption prose.
  - From Cursor-Requirements: Extend the `ship-pr-exit-matrix.md` update to rewrite line 37: all assessment tokens normalize to the combined adapter; the adapter consumes existing materialization inputs; legacy aliases do not relaunch independently. Add a negative harness assertion against `relaunch independently` and main-agent materialized-diff consumption language.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5: Specify executable, atomic normalization for legacy assessment aliases
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Alias normalization is specified only as prose, without a concrete operation or focused verification. Legacy aliases could reach the adapter unchanged, or normalization could drop unrelated handoff keys, reproducing the compatibility defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add an explicit normalization operation that atomically preserves all unrelated handoff keys, rewrites only `NEXT_ACTION` and the canonical `DETAIL`, and routes malformed input to the existing Tool Failures hard stop. Add a focused test that exercises the three handoff shapes rather than only asserting prompt wording.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: Conflict-resolution prose still routes post-rebase reassessment through legacy `NEXT_ACTION=guidelines-assessment`
- **Description**: Conflict-resolution prose still routes post-rebase reassessment through legacy `NEXT_ACTION=guidelines-assessment`. Scenario: After a successful `ship_pr_pre_push` rebase continue, operators following conflict-resolution.md are told the next ship relaunch will request fresh `guidelines-assessment` on `HEAD`/diff change, contradicting the scoped once-per-run adapter semantics and reintroducing per-alias orchestration outside the eight approved surfaces
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/references/conflict-resolution.md:85
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Conflict-resolution prose still promises guidelines-assessment reassessment on every HEAD change
- **Description**: Conflict-resolution prose still promises guidelines-assessment reassessment on every HEAD change. Scenario: After Piece 4 ships, conflict-resolution still tells the orchestrator that the next step-8-ship.sh relaunch will request NEXT_ACTION=guidelines-assessment whenever HEAD changed, contradicting scoped once-per-run reuse and the updated Step 8 adapter route outside this piece's eight surfaces
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/references/conflict-resolution.md:85
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

