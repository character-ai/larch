### OOS_1: `ACTION=FINALIZE` still requires a non-empty `voting-tally.md`; any tally abort that skips
- **Reviewer(s)**: Cursor-dyn-kv-contract
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/finalize-plan.sh:59-64
- **Description**: `ACTION=FINALIZE` still requires a non-empty `voting-tally.md`; any tally abort that skips writing a populated tally file breaks Step 4 unchanged by this KV refactor. Scenario: Step 4 `FINALIZE` hard-fails when `voting-tally.md` is missing or zero bytes even if earlier steps already logged a tally failure
- **Suggested fix**: Track as follow-up: relax finalize rules or guarantee `tally-plan-review.sh` always materializes `voting-tally.md` before non-zero exit
- **Phase**: design


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### OOS_2: Topology rows still point at plan-review.md only for plan review mechanics; new driver and
- **Reviewer(s)**: Cursor-dyn-scope-creep
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/shared/topology.tsv:4-8
- **Description**: Topology rows still point at plan-review.md only for plan review mechanics; new driver and aggregation hop are not reflected. Scenario: Consumer-facing topology counts or doc projections may drift after the PR
- **Suggested fix**: Land a small topology.tsv / docs/topology.md follow-up when updating the projection rules
- **Phase**: design


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=1 Result=neutral

### OOS_3: New Claude voter subprocess surface
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:1-200
- **Description**: New Claude voter subprocess surface. Scenario: launch-claude-review.sh on plan ballots changes trust and logging boundaries vs in-process Agent voter
- **Suggested fix**: Note subprocess data paths and any secret-handling expectations in SECURITY.md when implementation lands
- **Phase**: design


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### OOS_4: Ballot or accepted-plan field changes could break implement-side parsers
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/ (OOS / accepted-plan consumers)
- **Description**: Ballot or accepted-plan field changes could break implement-side parsers. Scenario: Downstream serialization surprises if headings change
- **Suggested fix**: Post-PR audit if FINDING template or tally outputs shift beyond current contracts
- **Phase**: design

Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

