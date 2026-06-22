### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Tail stable-ID mapping treats Codex combine reductions as issue-cap rollups
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: `_stable_ids_by_combined_item` in `python/oos_filer.py` (lines 162–182) assumes surplus source blocks always land in the last combined item, which matches `issue_cap` rollup but not arbitrary Codex combine merges. Codex can merge the first *k* blocks into item 1 (not the tail); the last combined item may receive tail stable IDs for sources it does not contain, so retry suppresses filing for blocks that were never filed. With `OOS_ISSUES_PER_RUN_CAP=99`, three source OOS blocks reduced to two valid blocks can record `OOS_3` on item 2 even when `OOS_3` was omitted. Limit tail rollup to confirmed post-cap paths, or map stable IDs from explicit combine/cap structure (or Codex source markers) instead of `blocks[combined_count - 1:]`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

