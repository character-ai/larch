# hook-bg-poll-guard.sh

## Purpose

PreToolUse guard that blocks `/design` progress-observation probes while an immediate-background wait marker is live.

## Primary callers

- `hooks/hooks.json` via the `PreToolUse` matcher `Read|Bash`.

## Invariants

- Fails open on malformed hook input, missing `jq`, unreadable or malformed markers, telemetry write failure, and unexpected runtime errors.
- Denies only progress-observation probes aimed at the live design tmpdir, task output files, result env files, reviewer output files, or `plan-review` artifacts.
- Allows wrapper-routed calls through `design-run-*.sh` so `/design` can launch or resume the background work.
- Allows only the Step 3 recovery waiter matched by `bash_is_step3_recovery_waiter` at the same tier as `bash_is_strict_wrapper_only`, before filetest-sleep denials.
- The Step 3 recovery waiter must use the exact `.completed/step-3-terminal` sentinel. An optional single leading `DESIGN_TMPDIR=<abs>;` assignment is accepted so the waiter resolves when the shell has not exported `$DESIGN_TMPDIR`; the bare `until` form still matches (#4489). Appended probes, compound command tails, and `.step3-review-result.env` waiters remain denied.
- Splits Step 3 sentinels. `.completed/step-3` remains the pause and Gate B milestone. `.completed/step-3-terminal` is the hook-release and recovery target written after `.step3-review-result.env` persists. `design-step3-review.sh` clears stale `.completed/step-3-terminal` and `.step3-terminal-persisted-this-run` at wrapper launch. `plan-review step3-state` clears them on direct re-entry and auto-continuation. Step 1e re-entry (`python/cli.py design step1e-reentry`) clears the same terminal sentinel pair alongside downstream phase markers.
- Releases a live `design-step3-review`, `design-step5c`, or `design-step-final-summary` marker once its terminal completion sentinel (`.completed/step-3-terminal` plus readable `.step3-terminal-persisted-this-run` for Step 3, `.completed/step-5c-terminal`, or `.completed/step-final-summary` respectively) exists, so the orchestrator can read the result artifact in the same turn the `<task-notification>` fired, before the background process's `EXIT`-trap marker cleanup runs (#4431, #4450). `.completed/step-5c` is an early in-wrapper sentinel only. Other guarded steps rely on the wrapper-routed read allowance.
- Allows a foreground terminal completion-sentinel probe after premature notification recovery. The allowance is syntax-based for `test -f …` or `[ -f … ]`, with an optional exact echo-only `&& echo DONE || echo WAIT` tail, and it allows the absent-sentinel `WAIT` case. It targets only `.completed/step-3-terminal`, `.completed/step-5c-terminal`, and `.completed/step-final-summary`. When live markers exist, the probe must bind `DESIGN_TMPDIR` to the live marker directory (explicit assignment matching a live dir, or exactly one live dir when unset). If the probed sentinel exists as a symlink at evaluation time, the guard denies it. Denies Bash commands that create or truncate terminal sentinel paths while a marker is live.
- Denies foreground probes of non-terminal sentinels, result envs, task outputs, progress artifacts, sleep loops, watcher loops, `plan-review/` artifacts, and appended `cat` / `ls` / `stat` / `jq` style probes. The foreground terminal probe is not a substitute for wrapper completion on the initial launch.
- Writes only the best-effort `$DESIGN_TMPDIR/bg-poll-guard-denials.count` telemetry sidecar.
- Does not echo raw probed paths in the deny reason.

## Harness

Covered by `scripts/test-hook-bg-poll-guard.sh`, wired through `make test-hook-bg-poll-guard` and `make lint`.
