## Proposed Design Outline

### Goals
- Fix #1: on emergency-repair relaunch with no repair branch started, re-check main CI health; if green, finalize as merged/SUCCESS via the normal run_postmerge_phase path.
- Fix #2: in postmerge-push-watch, auto-re-run failed jobs once before declaring postmerge-main-ci-fail; if the re-run passes, proceed normally without entering emergency-repair.
- Doc sweep: correct stale `python/ship.py` / `python/test_ship.py` prose references in SKILL.md and ship-pr-exit-matrix.md.

### Non-goals
- No changes to SKILL.md emergency-repair orchestration logic (postmerge-repair branch).
- No changes to the repair-shipped or stalled exit paths.
- No increase to the re-run attempt bound beyond 1.
- No changes to how pre-merge CI handles transient failures.

### Approach sketch
- Add `skip_flap_check: bool = False` to `MainHealthQuery` in `main_health.py`; propagate to `_classify_runs` to bypass `_same_sha_failure_flap` on explicit re-verify paths.
- In `ship.py` emergency-repair resume: if `EMERGENCY_REPAIR_BRANCH` is empty, call `read_main_health(skip_flap_check=True)` with `MAIN_REPAIR_HEAD`; if "pass", call `run_postmerge_phase` and return.
- In `ship.py` `_postmerge_main_health_gate`: on first "fail" (`counters.transient_retries < MAIN_HEALTH_MAX_TRANSIENT_RETRIES`), call `ci_monitor.rerun_failed`, write state with incremented `transient_retries` and `phase="postmerge-push-watch"`, return TRANSIENT.
- Pass `skip_flap_check=counters.transient_retries > 0` to `wait_main_health` in `_postmerge_main_health_gate` so the re-run's success is recognized.
- Add `MAIN_HEALTH_MAX_TRANSIENT_RETRIES: Final = 1` to `config.py`.

### Surfaces in scope
- `python/larch/implement/ship.py` (emergency-repair resume block, `_postmerge_main_health_gate`)
- `python/larch/implement/main_health.py` (`MainHealthQuery`, `_classify_runs`)
- `python/larch/core/config.py` (new constant)
- `skills/implement/references/postmerge-emergency-repair.md` (transient-recovery exit doc)
- `skills/implement/references/ship-pr-exit-matrix.md` (test path fix)
- `skills/implement/SKILL.md` (doc drift fix, 2 occurrences)
- `python/tests/implement/test_ship.py` (new tests)

### Open questions
- None.
