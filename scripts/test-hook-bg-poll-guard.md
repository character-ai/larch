# test-hook-bg-poll-guard.sh

## Purpose

Offline regression harness for `scripts/hook-bg-poll-guard.sh`.

## Primary callers

- `Makefile` target `test-hook-bg-poll-guard`.

## Invariants

- Exercises the shipped `hooks/hooks.json` registration and the guard's allow, deny, fail-open, stale-marker, wrapper-routed, Step 3 recovery-waiter, foreground terminal-sentinel probe, and telemetry paths.
- Covers positive `.completed/step-3-terminal` recovery waiters, the braced `${DESIGN_TMPDIR}` form, appended-probe denial, and continued `.step3-review-result.env` waiter denial.
- Covers live-marker foreground probes where terminal sentinels are absent and the expected result is `WAIT`.
- Pins symlink denial, non-terminal `step-3` / `step-5c` denial, result-env denial, sleep-loop denial, and appended `cat` / `ls` / `stat` / `jq` denial.
- Pins the Step 5c release split: `.completed/step-5c` does not release the marker, and `.completed/step-5c-terminal` does.
- Uses a temporary marker path supplied through `LARCH_BG_POLL_GUARD_MARKER`; it does not depend on a real Claude Code session.

## Harness

Run with `bash scripts/test-hook-bg-poll-guard.sh`.
