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
- Writes only the best-effort `$DESIGN_TMPDIR/bg-poll-guard-denials.count` telemetry sidecar.
- Does not echo raw probed paths in the deny reason.

## Harness

Covered by `scripts/test-hook-bg-poll-guard.sh`, wired through `make test-hook-bg-poll-guard` and `make lint`.
