### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Regression fixture does not match production vendor rows
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: important
- **Concern**: The regression fixture seeds `design` vendor rows instead of the production `implement` shape, so it can pass even when the live ledger still misses `gate-b-apply`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Rewrite fixtures with skill=implement vendor rows from the reproduction ledger; assert gate-b-apply is emitted against implement-skill predecessors


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Gate B start should ignore pre-round overlaps
- **Reviewer(s)**: dyn-dyn-timing-ledger
- **Severity**: important
- **Concern**: `_gate_b_apply_start_s` can use a pre-round overlapping design row that started before the current round window, which shortens the bar and can reintroduce a gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-timing-ledger: When deriving Gate B start, only consider rows with `row_start_s >= round_start_s` (or otherwise bound rows to the current round, e.g. by round directory/output basename prefix), then take `max(row_end_s)` over that filtered set.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

