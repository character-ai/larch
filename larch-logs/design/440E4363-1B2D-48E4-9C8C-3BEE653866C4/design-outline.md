## Proposed Design Outline

### Goals
- Stop the cross-lineage `fixer-rounds.tsv` crash: a foreign run-id row must not poison the next lineage's `_persist` / `_read_rounds`.
- Make the `BGJOB_RC != 0` fixer-lane outcome recoverable: route a crashed lane to `retry-next-tool` while tiers remain, `operator-bail` only when exhausted.
- Preserve a bounded redacted crash diagnostic into the committed run log so teardown no longer erases evidence.

### Non-goals
- Work item 4 (`complexity-baseline` prompt example in `_ci_launcher.py`): deferred.
- No change to bgjob daemon reap/result-env semantics; `daemon.py` and `model.py` are context only.
- No change to the complexity-baseline ratchet or `checks_run_relevant.py` CI-delegation scoping.

### Approach sketch
- Treat `fixer-rounds.tsv` as cross-lineage history: filter foreign run-id rows instead of raising; keep duplicate-attempt rejection scoped to the same run id; malformed rows still fail closed.
- Add a crashed-lane branch to `step-8-ci-fixer.sh --finalize` (triggered when `BGJOB_RC != 0` and the merge env is absent) that records the crashed tier in `lineage-$LINEAGE_KEY.tsv` and emits `retry-next-tool` or `operator-bail`; document the non-zero route in `ship-pr-ci-fix.md`.
- Append a bounded (~4 KiB) redacted diagnostic entry to `execution-issues.md` on a crashed lane from the Python finalize path; rely on the existing `run-log flush` to carry it past teardown.

### Surfaces in scope
- `python/larch/implement/ci_fixer_lane.py` (`_read_rounds`, `_persist`, `main` recovery)
- `skills/implement/scripts/step-8-ci-fixer.sh` (`--finalize` crashed-lane branch, missing-result guard)
- `skills/implement/references/ship-pr-ci-fix.md` (waterfall item 5 non-zero route)
- `python/tests/implement/test_ci.py` (cross-lineage and crash regression tests)

### Open questions
- None.
