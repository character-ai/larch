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
- The recovery waiter must use the exact `.completed/step-3` sentinel. Appended probes, compound command tails, and `.step3-review-result.env` waiters remain denied.
- Releases a live `design-step3-review`, `design-step5c`, or `design-step-final-summary` marker once its terminal completion sentinel (`.completed/step-3`, `.completed/step-5c-terminal`, or `.completed/step-final-summary` respectively) exists, so the orchestrator can read the result artifact in the same turn the `<task-notification>` fired, before the background process's `EXIT`-trap marker cleanup runs (#4431, #4450). Race-free: each wrapper writes its sentinel before the task process exits on terminal paths. Other guarded steps rely on the wrapper-routed read allowance.
- Writes only the best-effort `$DESIGN_TMPDIR/bg-poll-guard-denials.count` telemetry sidecar.
- Does not echo raw probed paths in the deny reason.

## Harness

Covered by `scripts/test-hook-bg-poll-guard.sh`, wired through `make test-hook-bg-poll-guard` and `make lint`.
