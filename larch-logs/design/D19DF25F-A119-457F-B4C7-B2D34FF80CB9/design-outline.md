## Proposed Design Outline

### Goals
- Fix 5 latent/nit defects in `design_log_ship.py`, `logging_util.py`, and `design-log-publish.sh`.
- Prevent silent required-check bypass, rerun budget waste, and log-file split across quiet-log dirs.
- Reduce duplication between `_classify_failed_run_for_rerun` and `evaluate_failure` upfront block.

### Non-goals
- Refactor the full `run_design_log_ci_merge` loop to use `poll_ci`.
- Change CI-wait timeouts or rerun budget limits.
- Add retry/backoff beyond what the existing config constants already provide.

### Approach sketch
- Finding 5 (active latent): guard `rerun_failed` call on `last_log_class.kind == "ready_transient"` only.
- Finding 2 (latent dedup): extract `_is_transient_failed_run` shared helper used by both `_classify_failed_run_for_rerun` and `evaluate_failure`.
- Finding 3 (nit): extend `logging_util.quiet_init` to check `DESIGN_TMPDIR` before `IMPLEMENT_TMPDIR`.
- Finding 4 (nit): split `2>&1` in the Python bridge into separate stderr redirect to a log file.
- Finding 1 (latent doc): add an inline comment in `run_design_log_ci_merge` noting the `required=True` invariant.

### Surfaces in scope
- `python/design_log_ship.py`
- `python/logging_util.py`
- `python/config.py` (if `ENV_DESIGN_TMPDIR` constant is missing)
- `scripts/design-log-publish.sh`
- `python/test_design_log_ship.py` (new test file)
- `python/test_logging_util.py` (if exists, else new)

### Open questions
- None.
