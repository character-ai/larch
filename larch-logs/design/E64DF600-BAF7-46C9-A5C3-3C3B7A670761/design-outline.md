## Proposed Design Outline

### Goals
- Add conservative path classification (`larch-logs/**` and `docs/**/*.md` = out-of-scope; all else = intersecting) to `architectural_guidelines.py`.
- Add `NOTE_STATE` field (authored / deterministic-clean / unavailable), separate authored-input and covered-input fingerprint identities, incremental coverage advancement, stale-input rejection, and prior-format compatibility to `architectural_guidelines.py`.
- Add `REASON_DETERMINISTIC_CLEAN` and `REASON_UNAVAILABLE` tokens with tolerant outcome classification to `ship_guidelines.py`; update schema v1 validators to accept new tokens; update docs.

### Non-goals
- Changing the live Step 8 dispatch route or inline authoring path (`dispatch_step18.py` or any non-listed file).
- Wiring the bgjob authoring lane (lanes 2/4, 3/4, 4/4).
- Adding new `assessment_kind` values to the outcome JSON beyond what schema v1 already allows.

### Approach sketch
- Add `NOTE_STATE_AUTHORED`, `NOTE_STATE_DETERMINISTIC_CLEAN`, `NOTE_STATE_UNAVAILABLE`, `REASON_DETERMINISTIC_CLEAN`, and `REASON_UNAVAILABLE` constants to `config.py`.
- Add `_path_out_of_scope(path)` helper in `architectural_guidelines.py`; extend the existing incremental check (`_head_change_larch_logs_only`) to cover `docs/**/*.md` via this helper.
- Add `AUTHORED_DIFF_FINGERPRINT` and `COVERED_DIFF_FINGERPRINT` as distinct sidecar fields alongside the existing `DIFF_FINGERPRINT`; old sidecars without them treat `DIFF_FINGERPRINT` as both (backward compat).
- Add deterministic-clean note writer, unavailable note writer, incremental-advancement helper, and stale-input checker to `architectural_guidelines.py`.
- Add `REASON_DETERMINISTIC_CLEAN`/`REASON_UNAVAILABLE` to `GUIDELINE_SHIP_REASON_TOKENS`/`INVARIANT_SHIP_REASON_TOKENS`; extend outcome classifiers in `ship_guidelines.py` for the new states; guard invariant violations from being overwritten by unavailable.

### Surfaces in scope
- `python/larch/core/config.py`
- `python/larch/core/architectural_guidelines.py`
- `python/larch/implement/ship_guidelines.py`
- `python/tests/core/test_architectural_guidelines.py`
- `python/tests/implement/test_ship.py`
- `docs/run-logs.md`, `docs/run-log-batches.md`

### Open questions
- None.
