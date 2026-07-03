### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Cumulative artifacts must stay fail-closed across tally short-circuits
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: important
- **Concern**: The tally flow should keep cumulative accepted artifacts intact while clearing only per-round state, and it should only append de-duplicated blocks after a successful full `_render` pass so zero-findings, vote-required, and tally-error paths cannot leak partial state into the cumulative files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add a test: successful round-1 tally populates cumulative files, then a failing round-2 tally leaves those files unchanged while per-round artifacts are cleared.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

