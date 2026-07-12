### OOS_1: [SCOPE-REDUCTION] Consider a thin shared `adjudicate_item()` helper instead of a full frozen dataclass engine
- **Description**: [SCOPE-REDUCTION] Consider a thin shared `adjudicate_item()` helper instead of a full frozen dataclass engine. Scenario: The issue needs one policy pass and one `_finding_oos_reroute_marker` owner, not necessarily frozen input/result dataclasses plus `run_items()` orchestration. `voting.py` already has `_ballot_blocks()` as a near-duplicate of `split_ballot()`. A dataclass-heavy engine may consume much of the 1200-line deletion budget and fail the net production-line gate without improving correctness.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/review/tally_engine.py
- **Phase**: design



