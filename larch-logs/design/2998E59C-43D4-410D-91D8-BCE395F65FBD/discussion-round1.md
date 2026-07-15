## Decision 1: Scope boundaries for Piece 5
- **Question**: Does Piece 5 introduce new test behavior or defer wiring from Pieces 2-4?
- **Resolution**: No. Piece 5 is reconciliation only: remove stale entries, sweep mechanical refs, validate coverage. All new test behavior is in Pieces 2-4.
- **Source**: issue body ("Do not introduce new test behavior or defer wiring required by Pieces 2-4")

## Decision 2: CI shard-count change condition
- **Question**: When should .github/workflows/ci.yaml be updated?
- **Resolution**: Only when `python/harness_ci_timing.py` measured shard totals show imbalance across the 5 harness shards. If balanced, leave matrix unchanged.
- **Source**: issue body ("only if measured shard timings justify a matrix change"); codebase has `python/harness_ci_timing.py` for timing queries.

## Decision 3: ARCHITECTURAL_INVARIANTS.md reference to test-step-7a.sh
- **Question**: After test-step-7a.sh is retired/shrunk by Pieces 2-4, does the invariant I-Flush-1 reference need updating?
- **Resolution**: Yes. The reference to `skills/implement/scripts/test-step-7a.sh` (line 76) should drop the bash harness citation; mechanical backing remains through `python/tests/implement/test_step_7a.py` only (if the bash harness is deleted) or updated to the thin smoke path.
- **Source**: codebase (ARCHITECTURAL_INVARIANTS.md:76)
