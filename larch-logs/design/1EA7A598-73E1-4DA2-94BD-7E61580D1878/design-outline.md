## Proposed Design Outline

### Goals
- Unify the "CI mergeable" definition so the merge gate accepts the same buckets as the CI monitor: "skipping", "cancelled", "neutral", "unknown" are acceptable.
- Add a stuck-bucket guard in the ship merge loop: bail with a clear diagnostic when `merge_pr` returns `CI_NOT_READY` too many consecutive times.

### Non-goals
- Do not change `ci_monitor._classify_checks_json` with `required=True` (the required path fails-closed correctly and stays as-is).
- Do not change the overall merge gate architecture or the `merge_pr` contract.
- Do not add a new CI-polling loop or change the `ci_monitor.monitor()` decision logic.

### Approach sketch
- In `gh._pr_checks_json_all_pass`: block only on `"fail"` and `"pending"` buckets; treat all other buckets as acceptable.
- In `gh._CHECKS_TEXT_BAD_RE`: remove "cancelled" and "skipping" from the bad-pattern regex; keep "fail", "pending", "in_progress", "queued".
- In `config.py`: add `SHIP_MERGE_CI_NOT_READY_BAIL_THRESHOLD: Final = 3`.
- In `ship.py` merge loop: track consecutive `CI_NOT_READY` from `merge_pr`; bail with a diagnostic when threshold is reached.

### Surfaces in scope
- `python/larch/git/gh.py` — `_pr_checks_json_all_pass`, `_CHECKS_TEXT_BAD_RE`
- `python/larch/core/config.py` — new threshold constant
- `python/larch/implement/ship.py` — merge-loop `CI_NOT_READY` handling
- `python/test_gh.py` — lenient JSON/text checks tests
- `python/test_ship.py` — stuck-bucket guard test
- `python/test_ci_monitor.py` — verify existing lenient test still passes

### Open questions
- None.
