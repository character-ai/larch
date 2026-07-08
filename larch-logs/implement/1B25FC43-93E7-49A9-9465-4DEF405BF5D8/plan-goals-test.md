## Goal
Implement issue #6595: [IMPLEMENTING] [BUG] bgjob implement-step5-review orphaned at exactly 123s when review-and-fix step5 dispatches Codex/Cursor reviewers.

## Implementation Plan
## Summary

The `bgjob implement-step5-review` consistently exits with `BGJOB_RC=orphaned` at exactly 123 seconds (BGJOB_OWNER_GRACE_S=120 + ~3s first-failure detection). This happens on every attempt regardless of whether prior round-1 artifacts exist. The bgjob daemon kills the review-and-fix child, terminating the review loop. Simple bgjobs with the same owner PID work fine, and the owner PID (the Claude Code process) validates correctly in all manual tests, making the root cause unclear.

## Original report

`bgjob implement-step5-review` orphaned at exactly 123s (3s + BGJOB_OWNER_GRACE_S) when `review-and-fix step5` runs with Codex/Cursor reviewers; simple bgjobs (`sleep 10`) with same owner PID succeed; owner PID (88801, Claude process) validates correctly in all manual tests; orphan is reproducible, always exactly 123s.

## Reproduction scenario

1. Run `/implement 6576 --merge` (MODERATE difficulty, Codex selected by bootstrap).
2. Step 2 (Codex dispatch) completes: `STATUS=complete`, `TOOL=codex`.
3. Step 3 (checks bgjob) completes: `BGJOB_RC=0 BGJOB_ELAPSED_S=132`.
4. Step 5 (`step-5-review.sh` bgjob): `BGJOB_STATUS=STARTED STEP=implement-step5-review PGID=<N>`.
5. `bgjob wait --step implement-step5-review --max-wait-s 270` returns `BGJOB_RC=orphaned BGJOB_ELAPSED_S=123`.
6. Retry Step 5: identical result at exactly 123s.
7. Third attempt (launched after a short interval): same result.

The orphan occurred with two other implement sessions' step5-review bgjobs live concurrently on different repos.

## Expected behavior

`bgjob implement-step5-review` should run to completion and return `BGJOB_RC=0` with valid `STEP5_REVIEW_STATUS=complete` (or `cap-hit`) in the result env.

## Observed behavior

The bgjob daemon kills the review-and-fix child at ~123s and writes `BGJOB_RC=orphaned` to the result env. This is exactly BGJOB_OWNER_GRACE_S (120s) plus the ~3s first-detection delay, meaning the daemon detected the owner process as missing at approximately t=3s into the run, then killed the child 120s later.

The bgjob stdout and stderr logs (`implement-step5-review.stdout.log`, `.stderr.log`) were both 0 bytes on the first two attempts. On the third attempt, the stderr log contained the Step 5 banner (printed at the start of `step5_run_child`), confirming the child did start executing. Round-1 specialist output files (Codex and Cursor reviewers) were present and timestamped approximately 12 minutes after the round start sentinel, suggesting those review subprocesses survived the orphan kill and ran to completion independently.

## Root cause analysis

Uncertain. The evidence is contradictory:

**Observed**: BGJOB_RC=orphaned at 123s means the bgjob daemon (which calls `validate_process_identity` for the owner PID every 1s) detected the owner as missing continuously for 120s starting at ~3s into the run.

**Contradiction**: The owner PID (the Claude Code process) validated correctly in all manual tests run from within the same session, including:
- 30 rapid consecutive checks at 100ms intervals: 0 failures.
- From a fork+setsid context (directly mimicking the daemon's environment): 0 failures.
- Between repeated bgjob attempts: the process was stable.

**Why step-5 but not step-3**: Step-3 checks (`run-step-checks.sh`) succeeded at 132s elapsed (> the 123s orphan threshold), ruling out a general owner-check sensitivity. The difference is that step-5's child calls `review-and-fix step5`, which dispatches multiple Codex and Cursor reviewer subprocesses. These reviewers use `start_new_session=True` and run for 10-15 minutes — they produced output files timestamped 12 minutes after round start despite the 123s kill.

**Most plausible hypothesis**: Something in the early execution of `review-and-fix step5` (within the first 3 seconds, likely during reviewer dispatch setup) triggers a condition that causes `ps -p <owner_pid> -o lstart= -o command=` — used inside `read_process_identity` — to return either empty output or a mismatched result when called from the bgjob daemon process. This might be a transient kernel-level issue under heavy concurrent subprocess load (multiple parallel Codex/Cursor sessions on the same machine), or a race in the macOS ps subsystem when many process groups are being created concurrently. The fact that the timing is exactly 123s (not variable) suggests a deterministic trigger at ~3s, not a random transient.

**Secondary hypothesis**: The bgjob daemon's `ps` call blocks for exactly 120s (a system-level timeout) and returns an error code, which `read_process_identity` maps to `None`, causing `validate_process_identity` to return `ok=False`. Because the _monitor loop has no timeout on `active_runner.run(["ps", ...])`, a 120s block in `ps` would not advance the `owner_missing_since` timer until `ps` returns. However, this would only set `owner_missing_since` once and then clear it on the next successful check — it cannot explain 120s of continuous failure.

## Evidence

- `BGJOB_RC=orphaned BGJOB_ELAPSED_S=123` across 3 independent attempts, each with a fresh bgjob start.
- 123s = BGJOB_OWNER_GRACE_S (120s, `python/larch/core/config.py:186`) + ~3s detection delay.
- `bgjob wait --step implement-step3-checks` returned `BGJOB_RC=0 BGJOB_ELAPSED_S=132` in the same session — 132 > 123, ruling out a general owner liveness issue.
- `validate_process_identity(recorded=<owner_identity>)`: 30 rapid checks returned `ok=True` in the same session.
- Same check from a fork+setsid child (mirroring the daemon's post-setsid context): 5/5 `ok=True`.
- Round-1 directory present with Codex and Cursor specialist output files timestamped ~12 minutes after `round-start-s` (Unix epoch `1783487259`), confirming subprocesses survived the 123s kill.
- `implement-step5-review.stderr.log` (after 3rd attempt): contained the Step 5 breadcrumb banner, confirming the child process started and reached `step5_run_child`.
- `step-5-review.sh` line 229: `--owner-pid "${LARCH_CLAUDE_PID:-$PPID}"` — LARCH_CLAUDE_PID is absent from `session-env.sh`, so $PPID (the Claude Code PID) is used.
- Two other implement sessions were running concurrent `implement-step5-review` bgjobs on different repo clones at the time.
- `python3 cli.py bgjob start --step implement-test-owner ... -- bash -c 'sleep 10'` with the same `--owner-pid`: returned `BGJOB_RC=0 BGJOB_ELAPSED_S=10` — simple commands work.

## Affected files

- `python/larch/bgjob/daemon.py`: `_monitor` loop — owner validation and orphan logic; `read_process_identity` call has no timeout, could block indefinitely.
- `python/larch/core/process_identity.py`: `read_process_identity` calls `ps` via `active_runner.run` with no timeout argument.
- `python/larch/core/proc.py`: `run` function — wraps `subprocess.run`; no default timeout, so a hung `ps` blocks the caller indefinitely.
- `skills/implement/scripts/step-5-review.sh`: `bgjob start` line — `--owner-pid "${LARCH_CLAUDE_PID:-$PPID}"`.
- `python/larch/review/round_runner.py`: dispatches Codex/Cursor reviewers; subprocess spawning behavior may stress the macOS process table.

## Suggested fix(es)

1. **Add orphan-reason logging**: before `_terminate_child_group(child_identity, reason="orphaned")`, log the last `ValidationResult.reason` (missing-pid, pgid-mismatch, start-time-mismatch, command-mismatch) to the bgjob stderr log. This would identify exactly which field mismatches on next occurrence.

2. **Add a timeout to `ps` calls in `read_process_identity`**: pass `timeout=5.0` (or similar) to `active_runner.run(["ps", ...])` so a hung `ps` invocation cannot block the monitor loop indefinitely. If `ps` times out, treat the owner as transiently unreachable (do NOT increment owner_missing_since until the failure persists across a configurable number of consecutive checks).

3. **Introduce a consecutive-failure threshold**: rather than starting the 120s grace period on the first validation failure, require N consecutive failures (e.g., N=3) before starting the timer. This prevents a single transient `ps` error from triggering a 120s countdown.

4. **Investigate reviewer subprocess spawning**: check whether `review-and-fix step5` or the Codex/Cursor launcher subprocess calls anything in the first 3 seconds that could transiently affect the macOS process table entry for the Claude PID (e.g., process group manipulation, `ptrace`-adjacent calls, or Node.js IPC mechanisms that affect sibling Node.js processes).

## Open questions

- What is the exact `ValidationResult.reason` when the daemon orphans the step-5 child? (missing-pid / pgid-mismatch / start-time-mismatch / command-mismatch — this is the most important diagnostic.)
- Does the issue reproduce when no other implement sessions are concurrently running step5-review bgjobs?
- Is the Claude Code process (88801) a Node.js process, and does the Codex CLI use any shared Node.js IPC or socket that could affect both processes simultaneously?
- Does the orphan still occur if Codex is unavailable and the review falls back to Cursor only (or Claude self-review)?
- Does the bgjob daemon's `ps` call use the same `ps` binary as the interactive manual tests?

## Test plan
(no test plan section in plan-file)
