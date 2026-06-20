## Goal
Implement issue #4867: [IMPLEMENTING] [BUG] /implement ship driver hangs after CI-fix push that triggers no fresh CI run.

## Implementation Plan
## Summary

The `/implement` Step 8+ ship driver can hang silently for ~30 minutes after its autonomous CI-fix pushes a fix commit. When the pushed fix commit does not trigger a fresh CI run, the driver's CI monitor (`python/ci_monitor.py`) cannot distinguish "CI pending (a run will appear)" from "no CI run was ever triggered for this head SHA" (zero checks). It polls a non-existent run for its full budget (180 polls x 10s), emits no `<task-notification>`, and never advances past `PHASE=ci-initial`. The correct fix sits unmerged on the PR and the operator is blocked with no signal until they manually discover and stop the hung task.

## Original report

`/implement` ship driver hangs ~30min after an autonomous CI-fix push when the fix commit does not trigger a fresh CI run.

Observed during `/implement --merge --emergency 4847` (larch 51.1.9, run 4802CF1A), PR #4863 in this repository.

Sequence:
1. Ship driver created the PR at commit `e90d88230`. CI failed on the harness pytest partition guard (`scripts/lint-harness-pytest-partition.py` via the `test-harness-shards-coverage` target): a newly added test `test_step3_loop_postplan_validator_runs_from_consumer_cwd` in `python/test_plan_review.py` was not covered by any `test-harnesses` shard `-k` filter (`python/test_plan_review.py: NOT a strict partition (full=66 union=65 ...)`, `not covered by any target: [...postplan_validator...]`).
2. The driver's autonomous CI-fix correctly diagnosed this and committed `a986462b3` ("Apply CI fixes (claude)"), a clean 1-line change adding `or postplan_validator` to the `test-review-design-step3-loop` Makefile target's `-k` filter, and pushed it to the PR branch. The fix is correct (the local partition guard passes on `a986462b3`).
3. HOWEVER, the push of `a986462b3` did NOT trigger a fresh CI run. `gh pr view <PR> --json statusCheckRollup` shows 0 checks on the new head; `gh run list --branch <branch>` shows ONLY the failed run on the prior commit `e90d88230`.
4. The driver's CI monitor (`ci_monitor: poll N/180 pending`) then polled for a CI conclusion on the new head that never arrived, hanging for ~30 minutes (the full 180-poll x 10s budget) WITHOUT emitting a `<task-notification>` and without advancing past `PHASE=ci-initial` in `ship-pr-state.sh`. The orchestrator was left blocked indefinitely; the background ship task was still running when manually stopped.

Impact: silent ~30-minute stall with no operator-visible signal; a correct CI fix is pushed but never validated or merged. The operator must manually discover the hang, stop the task, and take over.

Suspected fix direction: after an autonomous CI-fix commit+push, the driver assumes GitHub will re-run CI on the new head and polls for it. When no fresh `pull_request: synchronize` run is triggered for that SHA (observed here: 0 checks on `a986462b3`), the monitor consumes its entire poll budget against a non-existent run. The driver should (a) confirm a CI run actually started for the pushed head SHA within a short bounded window before entering the long poll loop, and re-trigger (or fail loudly) if none appears; and (b) emit a stall/completion signal instead of silently exhausting the poll budget.

Secondary observation: `/implement` Step 3/6 relevant-checks for a `python/test_*.py` edit do NOT run the harness pytest partition guard, so adding a test that is not covered by a shard `-k` filter passes all local checks and only fails in CI.

## Reproduction scenario

Hard to reproduce deterministically because it depends on GitHub not firing a `pull_request: synchronize` workflow for a pushed commit. Observed scenario:

1. Run `/implement --merge` on an issue whose implementation adds a test to an `ENFORCED` multi-target pytest file (e.g. `python/test_plan_review.py`) without updating any `test-harnesses` shard `-k` filter to cover it.
2. The PR is created; CI fails on the harness pytest partition guard.
3. The driver's autonomous CI-fix pushes a fix commit that covers the new test.
4. If GitHub does not trigger a fresh CI run for the pushed fix SHA (0 checks on the new head), the CI monitor polls "pending" for the full budget.

Synthetic reproduction of the monitor half: drive `python/ci_monitor.py`'s status loop against a branch head that has zero associated check runs and confirm it classifies as `pending` and polls to timeout rather than detecting "no run will start".

## Expected behavior

After an autonomous CI-fix commit+push, the driver should:
- Confirm a CI run actually started for the pushed head SHA within a short bounded window before entering the long poll loop.
- If no run appears in that window, re-trigger CI (or fail loudly with a stall/operator signal) rather than polling a non-existent run.
- In all cases emit a `<task-notification>` / advance `ship-pr-state.sh` so the orchestrator is never left silently blocked for the full poll budget.

## Observed behavior

- The fix commit `a986462b3` is pushed and becomes the PR head, but 0 checks are associated with it.
- `python/ci_monitor.py` classifies "no rows / pending" as `pending` and keeps polling (`poll N/180 pending`).
- The driver consumes its entire poll budget (~30 min), never emits a completion/stall signal, and never advances past `PHASE=ci-initial`.
- The orchestrator waits on a `<task-notification>` that never arrives; the background ship task is still running when manually stopped.

## Root cause analysis

Primary: `python/ci_monitor.py`'s status classifier cannot distinguish two states that both currently map to `pending`:
- "CI is queued/running and a conclusion will arrive" (legitimate pending), versus
- "No CI run exists for this head SHA and none will ever start" (zero checks).

When the autonomous CI-fix push does not trigger a fresh `pull_request` run, the monitor sees zero checks, classifies `pending`, and polls to timeout. The driver assumes a push always yields a fresh run, so it never verifies that a run actually started for the new head SHA before committing to the long poll loop. The absence of any `<task-notification>` on this path compounds the failure: the orchestrator has no signal to recover.

Inference (not confirmed): the reason the push did not trigger CI is GitHub-side (no `synchronize` event fired for `a986462b3`, or a concurrency/skip condition). This is environment-dependent, but the driver should be robust to it regardless of the cause.

Secondary (separate gap): `/implement` Step 3/6 relevant-checks for a `python/test_*.py` change do not include the harness pytest partition guard (`scripts/lint-harness-pytest-partition.py` / `test-harness-shards-coverage`). A test added to an `ENFORCED` file (the guard's hardcoded `ENFORCED` tuple includes `python/test_plan_review.py`) that is not covered by a shard `-k` filter passes all local checks and only fails in CI, which is what forced the autonomous CI-fix in the first place.

## Evidence

- PR head is the CI-fix commit `a986462b3` ("Apply CI fixes (claude)"), a 1-line `Makefile` change adding `or postplan_validator` to `test-review-design-step3-loop`; `git diff HEAD` is empty and the working tree is clean.
- The only CI run on the branch is on the prior commit `e90d88230` with conclusion `failure`; `gh pr view --json statusCheckRollup` returns length 0 for the current head; `mergeStateStatus` is `UNKNOWN`.
- The failed CI step output: `harness pytest partition guard: FAILED` / `python/test_plan_review.py: NOT a strict partition (full=66 union=65 targets=14)` / `not covered by any target: ['test_plan_review.py::test_step3_loop_postplan_validator_runs_from_consumer_cwd']`.
- `ship-pr-state.sh` shows `PHASE=ci-initial`, `CI_PASSED=false`, `STALL_TRACKING=true` (carried), `MERGE_RESULT=` empty, with the PR already created.
- The background ship task's captured stdout froze at `ci_monitor: poll 4/180 pending after 56s` (block-buffered), and `TaskStop` confirmed the task was still registered as running ~30 min later.
- `python/ci_monitor.py` header: "CI monitor loop: poll, classify, collect logs, fixer waterfall, GOTO-Rebase signal."; its classifier returns `pending` when there are pending rows or no rows.

## Affected files

- `python/ci_monitor.py` - the poll/classify loop that treats "zero checks" identically to "pending" and polls to timeout; needs a "no run started for head SHA" detection and a bounded startup window.
- `python/ship.py` - the Step 8+ driver that performs the autonomous CI-fix commit+push and re-enters CI monitoring; needs to verify a fresh run started for the pushed SHA (and re-trigger or emit a stall signal otherwise) and to guarantee a `<task-notification>`/state-advance on this path.
- `python/cli.py checks` / relevant-checks mapping (secondary) - does not select the harness pytest partition guard when an `ENFORCED` `python/test_*.py` file changes.
- `scripts/lint-harness-pytest-partition.py` / `scripts/test-harness-shards-coverage.sh` (secondary, context) - the guard whose failure triggered the autonomous CI-fix; its `ENFORCED` tuple includes `python/test_plan_review.py`.

## Suggested fix(es)

Primary (driver/monitor robustness):
- After an autonomous CI-fix push, verify a CI run actually started for the pushed head SHA within a short bounded window (e.g. a small number of short polls) before entering the long poll loop.
- If no run appears in that window, re-trigger CI for the head SHA (or fail loudly) rather than polling a non-existent run for the full budget.
- Ensure the CI-monitor/ship path always emits a `<task-notification>` and advances `ship-pr-state.sh` (to a recoverable stall) instead of silently consuming the entire poll budget.
- Optionally, have `python/ci_monitor.py` distinguish "0 checks / no run for head" from "pending" and surface it as a distinct, time-bounded condition.

Secondary (catch it earlier):
- Include `scripts/lint-harness-pytest-partition.py` (or `test-harness-shards-coverage`) in `/implement` Step 3/6 relevant-checks when an `ENFORCED` `python/test_*.py` file is changed, so an uncovered new test fails locally before PR/CI and the autonomous CI-fix is never needed for this class of failure.

## Open questions

- Why did the push of `a986462b3` not trigger a fresh `pull_request` CI run (GitHub `synchronize` event missing, a concurrency/skip rule, or push mechanism)? The driver should be robust regardless, but confirming the trigger gap may inform whether a deterministic re-trigger is needed.
- Should the bounded "did a run start" window re-trigger CI automatically (e.g. an empty commit or a closer/reopen), or stall to the operator with a clear message?
- Should the relevant-checks partition-guard inclusion run for every `python/test_*.py` change or only for files in the guard's `ENFORCED` set (to bound added local-check cost)?

## Test plan
(no test plan section in plan-file)
