## Proposed Design Outline

### Goals
- Add `python3 python/cli.py bgjob adapt` as a start-or-re-attach verb that encapsulates the adapter protocol shared by nine step scripts.
- Establish one documented liveness policy (`child OR daemon`) in a new module, eliminating the `and`/`or` drift.
- Ship unit tests for start, re-attach, stale-clear, merge-env, and liveness policy.

### Non-goals
- Converting any existing step script to use the new verb.
- Moving assessment or ship token vocabularies.
- Fixing `step-5-review.sh:75` `and` bug in-place (that is a consumer conversion, deferred).

### Approach sketch
- New `python/larch/bgjob/adapt.py` module: registry probe → liveness check → branch (start / re-attach / dead-fail-closed / done-early).
- New `adapt_main()` in `python/larch/bgjob/cli.py`; register it under `bgjob adapt` in `python/cli.py`.
- Liveness policy: `child_liveness(entry).live OR daemon_liveness(entry).live`; policy comment references daemon model.
- Stale-clear: unlink a dead entry and re-issue a fresh start.
- Re-attach path: emit `BGJOB_STATUS=STARTED STEP=<step> PGID=<pgid>` matching `bgjob start` contract so callers use `bgjob wait` unchanged.

### Surfaces in scope
- `python/larch/bgjob/adapt.py` (new)
- `python/larch/bgjob/cli.py` (new `adapt_main`)
- `python/cli.py` (register `bgjob adapt`)
- `python/tests/bgjob/test_bgjob_adapt.py` (new tests)

### Open questions
- None.
