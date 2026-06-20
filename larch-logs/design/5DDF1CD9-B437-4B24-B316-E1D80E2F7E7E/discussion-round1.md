## Decision 1: No-run reaction
- **Question**: When no CI run attaches to the PR head within the initial-start window, how should the ship driver react?
- **Resolution**: Stall recoverably — mirror #4867's `no-ci-checks-observed` bail (recoverable stall, emit notification + advance `ship-pr-state.sh`); operator re-triggers/resumes. No auto-re-trigger.
- **Source**: user

## Decision 2: CLI scope
- **Question**: Should the `--empty-checks-grace` default change for the `ci wait` / `ci status` CLI, or only the ship-driver merge loop?
- **Resolution**: Ship driver only. Leave the `ci wait` / `ci status` `--empty-checks-grace` default at `0` (opt-in). No behavior change for manual/cron callers.
- **Source**: user

## Decision 3: Periodic progress signal (non-goal)
- **Question**: Should this fix also add a periodic operator-visible progress/stall signal during long CI waits (run present but slow)?
- **Resolution**: Out of scope. The bounded initial-start window resolves the silent-hang failure mode for runless heads. Periodic-signal for slow-but-present runs is a separable enhancement (candidate OOS follow-up), NOT part of this fix.
- **Source**: user

## Decision 4: Initial-start window length
- **Question**: How long should the initial-start "did a run attach?" window be?
- **Resolution**: A dedicated new constant, larger than the 120s post-fix value (~300s). First runs legitimately take longer to attach; the stall is recoverable so over-waiting is cheap. Do NOT reuse `CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC`.
- **Source**: user

## Hard constraints (preserve)
- Do NOT change the post-fix-push path behavior from #4867 (`CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC` = 120s on head-changing re-entries).
- Do NOT change `ci wait` / `ci status` CLI default `--empty-checks-grace` (stays 0).
- Preserve `_resolve_checks_status` / `poll_ci` semantics when `empty_checks_grace == 0` (unchanged for all other callers, including `design_log_ship.py`).
- The NO_CHECKS bail must remain a recoverable stall that emits a `<task-notification>` and advances `ship-pr-state.sh` (no silent ~30-min hang).
