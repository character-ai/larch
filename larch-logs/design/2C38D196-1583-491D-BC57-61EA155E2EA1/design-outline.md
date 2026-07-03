## Proposed Design Outline

### Goals
- Close the three latent guideline-pin drift races named in the issue: closeout re-materialization (OOS_3), `note_fingerprint_stale`'s live-diff fallback (OOS_4), and non-atomic `materialize_implementation_diff` (OOS_6).
- Bring `closeout.py`'s pin flow to parity with the single-materialization pattern PR #6060 already established in `ship_guidelines.py`.
- Make `materialize_implementation_diff`'s merge-base and diff subprocess calls observe one consistent HEAD, closing the atomicity gap that also underlies OOS_4's residual risk.

### Non-goals
- No new abstractions, wrapper types, or a shared "materialize-once" helper module; reuse the existing `pin_note_from_staged_for_current_head` function as-is.
- No change to the `_pin_architectural_guidelines_note_best_effort` / `_pin_architectural_guidelines_note_once` external status contract (still returns `ok` / `skipped` / `failed`).
- No attempt to eliminate races that span separate process invocations over wall-clock time (e.g., ship-time pin vs. a later final-report staleness check); only same-call/internal non-atomicity is in scope.

### Approach sketch
- `python/larch/state/closeout.py`: replace `_pin_architectural_guidelines_note_best_effort`'s pin/refresh/retry block (up to 3 live-diff materializations) with one call to `architectural_guidelines.pin_note_from_staged_for_current_head`, mirroring the exact diff PR #6060 applied to `ship_guidelines.py`.
- `python/larch/core/architectural_guidelines.py`: in `materialize_implementation_diff`, resolve `HEAD` to an explicit SHA once via `git rev-parse HEAD`, then use that frozen SHA (not the literal `HEAD` ref) for both the `git merge-base` and `git diff` subprocess calls.
- `note_fingerprint_stale` (OOS_4) needs no separate code change: it already materializes at most once per call, and freezing `materialize_implementation_diff` (the function its live-diff fallback calls into) closes the residual internal-atomicity gap the issue describes.

### Surfaces in scope
- `python/larch/state/closeout.py`
- `python/larch/core/architectural_guidelines.py`
- `python/tests/state/test_closeout.py`
- `python/tests/core/test_architectural_guidelines.py`

### Open questions
- None.
