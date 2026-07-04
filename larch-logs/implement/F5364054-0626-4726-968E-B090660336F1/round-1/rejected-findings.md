### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: correctness: python/larch/calibration/difficulty.py:516-545
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `_last_plan_difficulty_line()` can let a later valid difficulty example in `## Acceptance` override the intended tier because it scans the whole document without respecting section boundaries. Scope the fallback to pre-`## Acceptance` or `## Plan` text, or take the last valid difficulty before `## Acceptance`; add a regression with a Testing-strategy trailer example.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

