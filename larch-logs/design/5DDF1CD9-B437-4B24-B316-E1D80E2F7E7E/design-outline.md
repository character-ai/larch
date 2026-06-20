## Proposed Design Outline

### Goals
- Bound the ship-driver's initial CI wait with a "did a run attach?" window, so a runless PR head fails loudly to a recoverable stall instead of a ~30-min silent hang.
- Reuse the existing #4867 `NO_CHECKS` -> `no-ci-checks-observed` recoverable-stall path (emits a `<task-notification>`, advances `ship-pr-state.sh`), now triggered on the initial wait too.

### Non-goals
- No change to the `ci wait` / `ci status` CLI `--empty-checks-grace` default (stays `0`; manual/cron callers unaffected).
- No periodic progress signal for slow-but-present runs (separable enhancement; candidate OOS).
- No change to the #4867 post-fix-push 120s grace, nor to other `empty_checks_grace=0` callers (`design_log_ship.py`).

### Approach sketch
- Add a dedicated `CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC` (~300s) constant in `python/config.py`, longer than the 120s post-fix value.
- In the `python/ship.py` merge loop, pass that grace on the initial wait (no prior observed run) instead of `0`; keep 120s for head-changing pushes.
- Generalize the existing `post_push_grace`-gated terminal `last_monitored_head` recording (and `_seed_last_monitored_head` resume) so the initial-grace `NO_CHECKS` bail records and resumes correctly.
- No logic change in `python/ci_monitor.py`; it already returns `NO_CHECKS` whenever `empty_checks_grace > 0`.

### Surfaces in scope
- `python/config.py` (new constant).
- `python/ship.py` (initial-wait grace + resume / terminal-head gating).
- Tests: `python/test_ship.py` (initial-wait no-run stall), `python/test_config.py` (constant); `python/test_ci_monitor.py` only if a new assertion is warranted.

### Open questions
- None. Scope resolved in Round 1.
