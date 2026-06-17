## Proposed Design Outline

### Goals
- Defer `larch_quiet_init` until after `session validate-design-tmpdir` in every embedded `_LEGACY_ASSETS` bash body that initializes quiet logging (the 7 quiet-before-validate scripts).
- Add a `validate-design-tmpdir` call (then quiet-init right after) to the 2 embedded scripts that init quiet but never validate.
- Add a universal decoded-asset test: every embedded script that calls `larch_quiet_init` must call `validate-design-tmpdir` before it.

### Non-goals
- No native in-process port of the retired scripts (C3a1 follow-up scope).
- No restoring deleted source `.sh` files or reading them from disk in `_materialize_legacy_root`.
- No behavior change beyond the quiet/validate ordering, plus the 2 added validate calls.

### Approach sketch
- Edit `python/plan_review.py`: regenerate the 9 affected `_LEGACY_ASSETS` blobs (decode -> move/add lines -> re-gzip+base64).
- Keep each script's top-of-file `source` lines (so `larch_err` stays available in `usage()`); move only the `larch_quiet_init` call.
- For `dispatch-plan-voters.sh` and `dispatch-plan-review-panel.sh`, round-trip via raw `_decode_asset` so the runtime waterfall-substitution markers survive; verify a decode-diff shows only the intended line changes.
- Add the invariant test to `python/test_plan_review.py`; update `SECURITY.md` (~line 166) to note the embedded assets now follow the ordering.

### Surfaces in scope
- `python/plan_review.py` (`_LEGACY_ASSETS` blobs).
- `python/test_plan_review.py` (new invariant test).
- `SECURITY.md` (ordering note).

### Open questions
- None.
