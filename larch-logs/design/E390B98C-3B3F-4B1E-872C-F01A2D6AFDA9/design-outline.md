## Proposed Design Outline

### Goals
- Clear the parent audit `oos-dropped-before-vote.md` when a round drops zero OOS items.
- Prevent downstream readers from mistaking a prior round's OOS drop set for the current run.

### Non-goals
- No changes to the per-round `review_tmpdir/oos-dropped-before-vote.md` write.
- No changes to `_apply_pre_vote_oos_gate` internals.
- No new gate logic or new data flow beyond the existing copy path.

### Approach sketch
- Remove the `if gate.dropped_count > 0:` call-site guard in `_prune_nit_then_pre_vote_gate`.
- Remove `gate.dropped_count <= 0 or` from `_copy_gate_audit_to_parent`'s early-return.
- When 0 drops, the function now copies the (empty) `dropped_file` to the parent, overwriting any stale content.
- Add one pytest that seeds a stale parent file, runs with 0 drops, and asserts the parent file is empty.

### Surfaces in scope
- `python/review_pipeline.py` (two guard removals)
- `python/test_review_pipeline.py` (one new test)

### Open questions
- None.
