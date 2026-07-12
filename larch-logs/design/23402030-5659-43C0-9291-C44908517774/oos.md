### FINDING_4: Preserve duplicate-heading hard failures
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `parse_blocks()` can return duplicate item IDs without failing, so direct delegation from `split_ballot()` could overwrite block files instead of preserving the existing diagnostic and exit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: After parsing, detect duplicate `item_id` values before writing block files; on duplicate, print the existing stderr diagnostic and raise `SystemExit(1)`. Add parity tests in `test_voting.py`.
  - From Cursor-Pragmatic: In the split_ballot rewrite, after parse_blocks enumerate blocks, fail with the existing duplicate stderr text and SystemExit(1) when item_id repeats; keep parity cases in test_voting.py.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_7: Define ballot grammar compatibility explicitly
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: `BALLOT_HEADING_RE` and `parse_blocks()` recognize different fenced and whitespace variants, so parser delegation can silently add or drop tally items despite the stated compatibility goal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Specify exact outcomes for both cases. Either declare them intentional convergence changes or add a canonical-parser compatibility mode that preserves the old contract


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [SCOPE-REDUCTION] Consider a thin shared `adjudicate_item()` helper instead of a full frozen dataclass engine
- **Description**: [SCOPE-REDUCTION] Consider a thin shared `adjudicate_item()` helper instead of a full frozen dataclass engine. Scenario: The issue needs one policy pass and one `_finding_oos_reroute_marker` owner, not necessarily frozen input/result dataclasses plus `run_items()` orchestration. `voting.py` already has `_ballot_blocks()` as a near-duplicate of `split_ballot()`. A dataclass-heavy engine may consume much of the 1200-line deletion budget and fail the net production-line gate without improving correctness.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/review/tally_engine.py
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

