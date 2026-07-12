## Proposed Design Outline

### Goals
- Replace the parallel `pre-coder` and `pre-self-review` snapshot implementations with one parameterized family `(snap_dir, prefix)`.
- Net line reduction in `snapshot.py`; each call site preserves its current root and artifact prefix.
- All existing snapshot-exercising tests pass unchanged.

### Non-goals
- No behavior changes to callers (`review_and_fix.py`, `coder_runner.py`).
- No changes to artifact naming conventions or on-disk layouts.
- No changes to `ValidatedPreCoderSnapshot` or public exports visible to callers.

### Approach sketch
- Extract shared write/validate/match/delta/collect logic into internal helpers parameterized by `(snap_dir: Path, prefix: str)`.
- Keep `pre_coder_snapshot_dir()` and `_self_review_snapshot_dir()` intact; root computation differs per family.
- Wrap shared core with thin pre-coder and self-review facades that supply their own root and prefix.
- Keep attempt-pre artifacts (`attempt-pre-*`) in the pre-coder-only layer; they have no self-review equivalent.

### Surfaces in scope
- `python/larch/review/snapshot.py`

### Open questions
- None.
