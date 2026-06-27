# hook-bg-poll-guard.sh

## Purpose

PreToolUse guard that blocks `/design` progress-observation probes while an immediate-background wait marker is live.

## Primary callers

- `hooks/hooks.json` via the `PreToolUse` matcher `Read|Bash`.

## Invariants

- Fails open on malformed hook input, missing `jq`, unreadable or malformed markers, telemetry write failure, and unexpected runtime errors.
- Denies only progress-observation probes aimed at the live design tmpdir, task output files, result env files, reviewer output files, or `plan-review` artifacts.
- Allows wrapper-routed calls through `design-run-*.sh` so `/design` can launch or resume the background work.
- Denies the Step 3 background sleep-loop recovery waiter matched by `bash_is_step3_recovery_waiter`, evaluated at the same tier as `bash_is_strict_wrapper_only` and before the generic filetest-sleep denials (#4725; this waiter was previously allowed at this tier). The waiter is itself a zero-output background task that amplifies premature `<task-notification>` events, so it is blocked in favor of the foreground terminal-sentinel probe below.
- The `bash_is_step3_recovery_waiter` matcher recognizes the exact `.completed/step-3-terminal` waiter shape — including an optional single leading `DESIGN_TMPDIR=<abs>;` assignment and the braced `${DESIGN_TMPDIR}` form (#4489) — so all of those bare-waiter forms are denied. Appended probes and compound command tails fall through to the generic deny loop; `.step3-review-result.env` waiters were already denied.
- Splits Step 3 sentinels. `.completed/step-3` remains the pause and Gate B milestone. `.completed/step-3-terminal` is the hook-release and recovery target written after `.step3-review-result.env` persists. `design-step3-review.sh` clears stale `.completed/step-3-terminal` and `.step3-terminal-persisted-this-run` at wrapper launch. `plan-review step3-state` clears them on direct re-entry and auto-continuation. Step 1e re-entry (`python/cli.py design step1e-reentry`) clears the same terminal sentinel pair alongside downstream phase markers.
- Releases a live `design-step3-review`, `design-step5c`, or `design-step-final-summary` marker once its terminal completion sentinel (`.completed/step-3-terminal` plus readable `.step3-terminal-persisted-this-run` for Step 3, `.completed/step-5c-terminal`, or `.completed/step-final-summary` respectively) exists, so the orchestrator can read the result artifact in the same turn the `<task-notification>` fired, before the background process's `EXIT`-trap marker cleanup runs (#4431, #4450). `.completed/step-5c` is an early in-wrapper sentinel only. Other guarded steps rely on the wrapper-routed read allowance.
- Allows a foreground terminal completion-sentinel probe after premature notification recovery. The allowance is syntax-based for `test -f …` or `[ -f … ]`, with an optional exact echo-only `&& echo DONE || echo WAIT` tail, and it allows the absent-sentinel `WAIT` case. It targets only `.completed/step-3-terminal`, `.completed/step-5c-terminal`, and `.completed/step-final-summary`. When live markers exist, the probe must bind `DESIGN_TMPDIR` to the live marker directory (explicit assignment matching a live dir, or exactly one live dir when unset). If the probed sentinel exists as a symlink at evaluation time, the guard denies it. Denies Bash commands that create or truncate terminal sentinel paths while a marker is live.
- Denies foreground probes of non-terminal sentinels, result envs, task outputs, progress artifacts, sleep loops, watcher loops, `plan-review/` artifacts, and appended `cat` / `ls` / `stat` / `jq` style probes. The foreground terminal probe is not a substitute for wrapper completion on the initial launch.
- Clamps repeated foreground terminal-sentinel probes (#5478). The sanctioned recovery pattern is one foreground probe per real `<task-notification>`; spurious empty-output notifications (#5240) can drive the orchestrator to probe every turn while the sentinel stays absent. The hook counts consecutive foreground probes per sentinel while the sentinel is absent and denies once the count exceeds `LARCH_BG_POLL_GUARD_PROBE_THRESHOLD` (default 2). The counter is keyed per sentinel basename, so Step 3 (`step-3-terminal`) and Step 5c (`step-5c-terminal`) waits in one tmpdir cannot contaminate each other, and it clears when the sentinel becomes present (the marker-release path). The deny clears on its own once the sentinel appears. Denying a probe never blocks completion detection, which depends on marker release, not the probe. Fails open (allows) when the per-sentinel counter cannot be written.
- Writes only best-effort counter sidecars under `$DESIGN_TMPDIR`: `bg-poll-guard-denials.count` (aggregate denial telemetry) and the per-sentinel `bg-poll-guard-probe-denials.<sentinel>.count` files that drive the #5478 foreground-probe clamp.
- Does not echo raw probed paths in the deny reason.
- Emits deny JSON with a static `printf` string, not `jq -cn`, once a deny branch is reached (#5610). `jq` is still required up front to parse the hook input (the hook fails open when `jq` is missing before parsing), but the final deny emission does not depend on `jq`, so a `jq` runtime failure at emit time cannot silently swallow the deny output.

## Harness

Covered by `scripts/test-hook-bg-poll-guard.sh`, wired through `make test-hook-bg-poll-guard` and `make lint`.
