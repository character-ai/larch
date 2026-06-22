## Goal
Implement issue #5066: [IMPLEMENTING] [BUG] Ship driver CI monitor freezes at 'poll N pending' with no transition….

## Implementation Plan
## Summary

During an `/implement --merge` run, the Python ship driver's CI monitor appeared to hang while "watching CI": its progress output froze at `ci_monitor: poll 2/180 pending after 18s` and emitted nothing further for tens of minutes, even though the PR's CI had actually completed (with failures) on GitHub. The driver process stayed alive but produced no new breadcrumbs, so the operator could not tell whether the run was still polling, had detected completion, was hung in a subprocess, or had silently moved into a downstream phase. The root cause is most likely a `gather_status` `gh` call that can block without a subprocess timeout, compounded by an observability gap: the monitor emits a breadcrumb only on the "still pending" branch, so a frozen or post-suspend monitor is indistinguishable from normal slow CI.

## Original report

why ship driver got stuck watching CI

(Context: observed live during an `/implement --merge` recovery run. The operator noticed there was no CI job ongoing while the driver still reported "poll 2/180 pending", and asked whether the monitor was watching a stale/failed run from earlier.)

## Reproduction scenario

Not deterministically reproduced; the hang depends on an external `gh`/network condition (or host suspend) during polling. Best-effort scenario:

1. Run `/implement --merge <issue>` so the Python ship driver reaches the CI monitor (`PHASE=ci-initial`).
2. While the monitor is polling (`ci_monitor: poll N/180 pending ...`), induce a stall in the underlying `gh pr view` call — e.g., a network partition, a `gh` auth/rate-limit stall, or a host sleep/suspend between polls.
3. Observe that the breadcrumb stream freezes at the last printed `poll N` line and no further breadcrumb appears, while the process remains alive and GitHub CI continues to completion independently.

A faster path to confirm the observability half: let CI complete (pass or fail) and note that `poll_ci` returns with no terminal breadcrumb marking the transition out of polling.

## Expected behavior

- The CI monitor should not block indefinitely on a single `gh` status query; a hung query should hit a subprocess timeout, count toward `CI_MONITOR_STATUS_FAILURE_BAIL`, and either retry or bail with a clear breadcrumb.
- The operator-visible breadcrumb stream should make the monitor's state legible: a heartbeat/transition line when polling exits (CI complete / failed / no-checks / bail), and ideally an indication when a poll query is in-flight or when a long real-time gap (host suspend) was detected.
- A frozen monitor should be distinguishable from a normally-slow CI run.

## Observed behavior

- Breadcrumb output froze at `ci_monitor: poll 2/180 pending after 18s; sleeping 10s` and never advanced (no `poll 3`, no transition line).
- The driver process (`python/cli.py ship pr ... --merge true`) remained alive for tens of minutes after the freeze.
- The PR's CI had actually completed with failures on GitHub during that window; `gh pr checks` showed all checks `COMPLETED` while the monitor still implied "pending".
- Because there was no terminal/heartbeat breadcrumb, the run looked "stuck watching CI" with no signal about what it was doing.

## Root cause analysis

Primary hypothesis (high confidence on the observability gap; medium confidence on the exact blocking site):

1. **No subprocess timeout on the poll-time status query.** `gather_status` calls `gh.pr_view` → `gh.pr_view_read` → `_retry_read(...)` with no `timeout` argument. If the underlying `gh pr view` subprocess blocks (network partition, auth/rate-limit stall, or a connection hung across a host suspend), `gather_status` never returns, so the next `poll_ci` iteration never prints its `poll N` breadcrumb. The monitor is then frozen inside a status query rather than in `sleep`, and the `CI_MONITOR_STATUS_FAILURE_BAIL=3` safety net never triggers because a hang is not an error return.

2. **Observability gap in `poll_ci`.** The `ci_monitor: poll N/M pending ...` breadcrumb is emitted only on the `decision.action == "wait"` branch (after the early `return status, decision` for any non-wait decision). There is no breadcrumb when `poll_ci` exits (merge/fix/rebase/bail), no "CI complete: <conclusion>" line, and no heartbeat while a `gather_status` query is in flight. So a frozen monitor and a monitor that has simply moved on both look identical from the breadcrumb stream: the last visible line is a stale `poll N pending`.

Contributing factor (uncertain): **host suspend.** `poll_ci` uses `time.monotonic`, which pauses during macOS sleep. If the host slept after poll 2, the process was suspended and the clock paused; the `_CI_SUSPEND_THRESHOLD_SEC = 60.0` guard (which decrements `checks` when a poll iteration's wall delta is large) only adjusts the counter, it does not surface a breadcrumb explaining the gap. This would produce the same "frozen at poll 2" symptom without any code-level hang.

It is not yet confirmed which of (1) or the suspend factor was active in the observed run; both yield the identical operator-facing symptom, and the fix for the observability gap (2) plus a status-query timeout (1) addresses the run regardless.

Note: output buffering was ruled out — `_warn_stderr` routes through `logging_util.BreadcrumbWriter().emit`, which flushes its stream (`stream.flush()`), so the frozen output reflects the real emission, not a buffered backlog.

Related prior work (distinct cause, not a duplicate): #4877 and #4867 fixed the adjacent *empty-checks* failure mode — a silent ~30-minute poll when **no CI run ever starts** for the PR head — via `empty_checks_grace` / `empty_checks_startup_deadline_sec`. This report is the complementary case: CI **did** start and complete, but the monitor froze mid-poll. The two known causes there (no fresh run / empty checks) do not cover a hung `gather_status` query or a paused-clock suspend, and #4877's own committed Code Flow diagram shows `gather_status → gh pr view + git fetch + checks_status` with no per-call timeout, consistent with the blocking-site hypothesis here.

## Evidence

- `python/ci_monitor.py` `poll_ci`: the `ci_monitor: poll {checks}/{max_polls} pending after {elapsed:.0f}s; sleeping {poll_interval:.0f}s` breadcrumb is emitted via `_warn_stderr` only after the `if decision.action != "wait": return status, decision` early-return — i.e., never on completion/transition.
- `python/ci_monitor.py` `gather_status`: calls `gh.pr_view(runner, pr, repo=repo, cwd=cwd)` and `_resolve_checks_observation(...)` with no per-call timeout threaded from the poll loop.
- `python/gh.py` `pr_view_read`: calls `_retry_read(runner, [...], cwd=cwd)` with no `timeout` argument (contrast with `python/ci_monitor.py` sites that pass `config.SUBPROCESS_DEFAULT_TIMEOUT_SEC`, e.g. around the failed-jobs/log-collection calls, and the agentic-fix delegate timeout).
- `python/logging_util.py` `BreadcrumbWriter.emit`: performs `stream.flush()`, so breadcrumbs are not block-buffered (buffering ruled out).
- `python/config.py`: `CI_WAIT_TIMEOUT_SEC = 1800`, `CI_WAIT_POLL_INTERVAL_SEC = 10` (so `max_polls = 180`), `CI_MONITOR_STATUS_FAILURE_BAIL = 3`; `_CI_SUSPEND_THRESHOLD_SEC = 60.0` in `python/ci_monitor.py`.
- Observed run: the ship-driver background task's captured output ended exactly at `ci_monitor: poll 2/180 pending after 18s; sleeping 10s`; the `ship pr` process remained alive; `gh pr checks` for the PR showed all checks `COMPLETED` (with several failures) during the same window.

## Affected files

- `python/ci_monitor.py` — `poll_ci` (breadcrumb only on the wait branch; no transition/heartbeat line; `_CI_SUSPEND_THRESHOLD_SEC` counter adjustment is silent) and `gather_status` (no timeout threaded into its `gh` query).
- `python/gh.py` — `pr_view_read` / `pr_view` (no subprocess timeout on the poll-time status read).
- `python/config.py` — CI wait/poll/timeout/bail tunables relevant to any timeout or heartbeat added.

## Suggested fix(es)

- Thread a subprocess timeout into the poll-time status query so a hung `gh pr view` cannot block `gather_status` forever; on timeout, treat it as a status failure that counts toward `CI_MONITOR_STATUS_FAILURE_BAIL` (retry, then bail with `CI_WAIT_BAIL_STATUS_STALE`) and emit a breadcrumb.
- Add a terminal/transition breadcrumb when `poll_ci` exits the loop (e.g. `ci_monitor: CI <conclusion> after Ns -> <action>`), so the operator can see polling ended and why.
- Optionally emit a lightweight heartbeat around each in-flight `gather_status` call (or a "query N in progress" line) so a hang inside the query is visible rather than presenting as a stale `poll N pending`.
- When the suspend guard (`_CI_SUSPEND_THRESHOLD_SEC`) fires, emit a breadcrumb noting a large real-time gap / probable host suspend so a non-advancing poll counter is explained.

## Open questions

- In the observed run, was the freeze a `gh pr view` hang (no timeout) or a host suspend (paused monotonic clock), or both? Confirming would narrow the primary fix, though both are worth addressing.
- Should a poll-time status-query timeout reuse `config.SUBPROCESS_DEFAULT_TIMEOUT_SEC`, or a dedicated (shorter) CI-status timeout so a single slow query does not consume a large share of the poll interval?
- Should the monitor proactively re-resolve and re-orient (re-query head SHA / latest run) after detecting a large suspend gap, given CI may have completed while the host slept?

## Test plan
(no test plan section in plan-file)
